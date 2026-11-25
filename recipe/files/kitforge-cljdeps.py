#!/usr/bin/env python3
"""kitforge-cljdeps.py — ReadyStack kit helper for Clojure CLI (tools.deps) builds.

  inject <deps.edn> <group/artifact>=<version> ...
      Raise each lib to at least <version> as a TOP-LEVEL coordinate of the project's :deps map. tools.deps lets a
      top-level dep win over every transitive version, so this reaches libraries merged into an uberjar. An
      existing top-level entry is raised in place (never lowered); a missing one is added.
  verify <dir> <group/artifact>=<version> ...
      Every jar under <dir> that embeds META-INF/maven/<group>/<artifact>/pom.properties must carry a version at
      or above the floor. Fails closed: an override that did not take must not reach the image.
  normalize <dir> <epoch>
      Rewrite every jar under <dir> with entries in name order (META-INF/ and the manifest first), one fixed
      timestamp and no extra fields, so the archive bytes do not depend on when or where it was built.
  shadowdet <shadow-cljs.edn> <agent.jar>
      Make a shadow-cljs release reproducible (no-op when the file is absent): :parallel-build false in every build,
      and top-level :jvm-opts that load the name-hash agent (built at <agent.jar>) for Closure's JSChunk and pin the
      default identity-hash mode in shadow's JVM. See SHADOW_NOTE below.
  hashagent <agent.jar>
      Compile AGENT_JAVA with the build JDK's javac into the build-time javaagent jar (see the notes above AGENT_JAVA:
      name-hash, reflect:<prefix> and dirsort modes). The offline stage loads it through JAVA_TOOL_OPTIONS.
"""
import os, re, sys, time, zipfile

# SHADOW_NOTE (metabase chain 543, 2026-10-20). Two serial-vs-parallel facts measured on Metabase v0.64.2.8's
# `shadow-cljs release app` (571 output files): two default runs differed in ~340 files, two serial runs in ~190, two
# serial runs with the agent in 0, two parallel runs with the agent in ~160.
#  * The serial runs' per-namespace compiler output was identical (only :compiled-at differed), so the residual came
#    from optimisation. shadow-cljs's ReplaceCLJSConstants pass collects the chunks that use each keyword constant in a
#    HashSet<JSChunk> and folds getDeepestCommonDependencyInclusive over it; with no unique deepest common dependency
#    the result depends on the fold order, i.e. on JSChunk identity hashes, so constants (":joins") moved between
#    chunks and Closure's frequency-ranked renaming of every global shifted with them. The agent gives JSChunk a
#    hashCode() from its final name (the namespace), so the set order is a function of the build.
#  * Parallel compile itself also varies the output, so every build gets :parallel-build false.
# shadow's launcher passes top-level :jvm-opts to the JVM as -J flags; that is how the agent reaches it even when the
# product's build scrubs the environment (Metabase's :frontend step passes bun only PATH and HOME). -XX:hashCode=5 is
# HotSpot's default, restated so that a JAVA_TOOL_OPTIONS -XX:hashCode=2 meant for the Clojure AOT compile (see the
# renderer) can never reach Closure, whose AST-keyed hash maps make a constant identity hash take minutes, not seconds.
SHADOW_AGENT_TARGETS = "com.google.javascript.jscomp.JSChunk"

# The build-time javaagent (kitforge-namehash.jar, built from this source by `hashagent`; never in the image). Plain
# class-file bytes, no library. Its argument is a comma list of modes:
#   <class>          give the class `public int hashCode() { return Objects.hashCode(this.name); }`: for classes that keep
#                    identity equality and a final String name field but are iterated through hash collections whose
#                    order reaches the output (Closure's JSChunk in shadow-cljs, SHADOW_NOTE). A named class without a
#                    final instance field `String name` halts the JVM (exit 97); one that defines hashCode() is left alone.
#   reflect:<prefix> in classes under the prefix, rewrite each invokevirtual of Class.get{,Declared}{Methods,Constructors,
#                    Fields} into an invokestatic of a helper that returns the same array sorted (name, parameter types,
#                    return type, declaring class). Same length and stack effect, so offsets and StackMapTables stand.
#   dirsort          in every class outside the JDK, the same for File.list/listFiles (sorted, null kept).
# Why the two rewrites (metabase chain 543, 2026-10-21): HotSpot sorts a class's methods by the ADDRESS of
# their name symbols, and with symbols on the C heap that order varies from run to run for methods that share a name
# (measured: 16 of 30 JVMs listed Quartz StdJDBCDelegate's two selectTriggerForFireTime overloads one way, 14 the other,
# under -Xshare:off; a busy compile JVM behaves the same). Clojure's gen-class keys its method maps on [name params
# return] (identical hashes under -XX:hashCode=2), so its overload order and its static Var fields followed that coin
# flip: the canonical build and the drive's own repro of chain 543 differed in the four gen-class Quartz delegates.
# And metabase's build compiles its drivers in (.listFiles modules/drivers) order, which is ext4 directory-hash order:
# stable on one host, different on the next (<redacted: internal host> hive-like first, <redacted: internal host> databricks), shifting every later gensym.
# Only reflection inside Clojure's own classes (gen-class, deftype/reify bridges, the compiler's interop resolution) is
# sorted; the product's and libraries' code keeps the JVM's order. The compiler writes class files from the bytes it
# generated, so the rewrite changes how the build JVM behaves, never the bytes of a compiled class.
AGENT_JAVA = r"""
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileFilter;
import java.io.FilenameFilter;
import java.io.IOException;
import java.lang.instrument.ClassFileTransformer;
import java.lang.instrument.Instrumentation;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.ProtectionDomain;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class KitforgeNameHash implements ClassFileTransformer {
    // name-hash targets: class gets hashCode() from its final String name
    final Set<String> targets = new HashSet<>();
    // reflect:<prefix>: in classes under the prefix, Class.get{,Declared}{Methods,Constructors,Fields} come back sorted
    final List<String> reflectPrefixes = new ArrayList<>();
    // dirsort: in every class outside the JDK, File.list/listFiles come back sorted
    boolean dirsort;

    static final String SELF = "KitforgeNameHash";
    // {owner, name, descriptor, helper}: an invokevirtual of owner.name:descriptor becomes invokestatic SELF.helper
    static final String[][] REFLECT = {
        {"java/lang/Class", "getMethods", "()[Ljava/lang/reflect/Method;", "getMethods"},
        {"java/lang/Class", "getDeclaredMethods", "()[Ljava/lang/reflect/Method;", "getDeclaredMethods"},
        {"java/lang/Class", "getConstructors", "()[Ljava/lang/reflect/Constructor;", "getConstructors"},
        {"java/lang/Class", "getDeclaredConstructors", "()[Ljava/lang/reflect/Constructor;", "getDeclaredConstructors"},
        {"java/lang/Class", "getFields", "()[Ljava/lang/reflect/Field;", "getFields"},
        {"java/lang/Class", "getDeclaredFields", "()[Ljava/lang/reflect/Field;", "getDeclaredFields"}};
    static final String[][] DIRS = {
        {"java/io/File", "list", "()[Ljava/lang/String;", "list"},
        {"java/io/File", "list", "(Ljava/io/FilenameFilter;)[Ljava/lang/String;", "listNamed"},
        {"java/io/File", "listFiles", "()[Ljava/io/File;", "listFiles"},
        {"java/io/File", "listFiles", "(Ljava/io/FileFilter;)[Ljava/io/File;", "listFilesFiltered"},
        {"java/io/File", "listFiles", "(Ljava/io/FilenameFilter;)[Ljava/io/File;", "listFilesNamed"}};

    public static void premain(String args, Instrumentation inst) {
        KitforgeNameHash t = new KitforgeNameHash();
        for (String c : (args == null ? "" : args).split(",")) {
            if (c.isEmpty()) continue;
            if (c.equals("dirsort")) t.dirsort = true;
            else if (c.startsWith("reflect:")) t.reflectPrefixes.add(c.substring(8).replace('.', '/'));
            else t.targets.add(c.replace('.', '/'));
        }
        inst.addTransformer(t);
    }

    public byte[] transform(ClassLoader loader, String name, Class<?> redefining, ProtectionDomain pd, byte[] b) {
        if (name == null || redefining != null || name.startsWith(SELF)) return null;
        try {
            if (targets.contains(name)) {
                byte[] out = patchHashCode(b);
                System.err.println("kitforge-namehash: " + name + (out == null ? " already defines hashCode(); unchanged"
                                                                               : ".hashCode() derives from its name"));
                return out;
            }
            // the rewritten call sites name this agent's class: only loaders that can see it (the application loader
            // and its children; the agent jar is on the system class path)
            if (loader == null || loader == ClassLoader.getPlatformClassLoader()) return null;
            List<String[]> rules = new ArrayList<>();
            for (String p : reflectPrefixes) if (name.startsWith(p)) { rules.addAll(Arrays.asList(REFLECT)); break; }
            if (dirsort && !jdk(name)) rules.addAll(Arrays.asList(DIRS));
            if (rules.isEmpty() || !mentions(b, rules)) return null;
            return rewriteCalls(b, rules);
        } catch (Throwable t) {
            System.err.println("kitforge-namehash: cannot patch " + name + ": " + t);
            Runtime.getRuntime().halt(97);
            return null;
        }
    }

    // cheap prefilter: a class whose bytes never spell one of the rules' method names has no call site to rewrite
    static boolean mentions(byte[] b, List<String[]> rules) {
        for (String[] r : rules) {
            byte[] n = r[1].getBytes(StandardCharsets.UTF_8);
            outer:
            for (int i = 0; i + n.length <= b.length; i++) {
                for (int j = 0; j < n.length; j++) if (b[i + j] != n[j]) continue outer;
                return true;
            }
        }
        return false;
    }

    static boolean jdk(String n) {
        return n.startsWith("java/") || n.startsWith("javax/") || n.startsWith("jdk/") || n.startsWith("sun/")
            || n.startsWith("com/sun/");
    }

    // ---- the helpers the rewritten call sites invoke -------------------------------------------------------------
    static String sig(Class<?>[] ps) {
        StringBuilder s = new StringBuilder();
        for (Class<?> p : ps) s.append(p.getName()).append(';');
        return s.toString();
    }
    static final Comparator<Method> BY_METHOD = new Comparator<Method>() {
        public int compare(Method a, Method b) {
            int c = a.getName().compareTo(b.getName());
            if (c == 0) c = sig(a.getParameterTypes()).compareTo(sig(b.getParameterTypes()));
            if (c == 0) c = a.getReturnType().getName().compareTo(b.getReturnType().getName());
            if (c == 0) c = a.getDeclaringClass().getName().compareTo(b.getDeclaringClass().getName());
            return c;
        }
    };
    static final Comparator<Constructor<?>> BY_CTOR = new Comparator<Constructor<?>>() {
        public int compare(Constructor<?> a, Constructor<?> b) {
            return sig(a.getParameterTypes()).compareTo(sig(b.getParameterTypes()));
        }
    };
    static final Comparator<Field> BY_FIELD = new Comparator<Field>() {
        public int compare(Field a, Field b) {
            int c = a.getName().compareTo(b.getName());
            if (c == 0) c = a.getDeclaringClass().getName().compareTo(b.getDeclaringClass().getName());
            return c;
        }
    };
    public static Method[] getMethods(Class<?> c) { Method[] m = c.getMethods(); Arrays.sort(m, BY_METHOD); return m; }
    public static Method[] getDeclaredMethods(Class<?> c) {
        Method[] m = c.getDeclaredMethods(); Arrays.sort(m, BY_METHOD); return m; }
    public static Constructor<?>[] getConstructors(Class<?> c) {
        Constructor<?>[] m = c.getConstructors(); Arrays.sort(m, BY_CTOR); return m; }
    public static Constructor<?>[] getDeclaredConstructors(Class<?> c) {
        Constructor<?>[] m = c.getDeclaredConstructors(); Arrays.sort(m, BY_CTOR); return m; }
    public static Field[] getFields(Class<?> c) { Field[] f = c.getFields(); Arrays.sort(f, BY_FIELD); return f; }
    public static Field[] getDeclaredFields(Class<?> c) {
        Field[] f = c.getDeclaredFields(); Arrays.sort(f, BY_FIELD); return f; }
    public static String[] list(File d) { String[] r = d.list(); if (r != null) Arrays.sort(r); return r; }
    public static String[] listNamed(File d, FilenameFilter f) {
        String[] r = d.list(f); if (r != null) Arrays.sort(r); return r; }
    public static File[] listFiles(File d) { File[] r = d.listFiles(); if (r != null) Arrays.sort(r); return r; }
    public static File[] listFilesFiltered(File d, FileFilter f) {
        File[] r = d.listFiles(f); if (r != null) Arrays.sort(r); return r; }
    public static File[] listFilesNamed(File d, FilenameFilter f) {
        File[] r = d.listFiles(f); if (r != null) Arrays.sort(r); return r; }

    // ---- class-file reading --------------------------------------------------------------------------------------
    static final class Pool {
        int countPos, count, end;
        int[] tag, r1, r2;
        String[] utf;
        Pool(ByteBuffer in) throws IOException {
            if (in.getInt() != 0xCAFEBABE) throw new IOException("not a class file");
            in.getShort(); in.getShort();
            countPos = in.position();
            count = in.getShort() & 0xffff;
            tag = new int[count]; r1 = new int[count]; r2 = new int[count]; utf = new String[count];
            for (int i = 1; i < count; i++) {
                int t = in.get() & 0xff;
                tag[i] = t;
                switch (t) {
                    case 1: { int len = in.getShort() & 0xffff; byte[] s = new byte[len]; in.get(s);
                              utf[i] = new String(s, StandardCharsets.UTF_8); break; }
                    case 3: case 4: in.getInt(); break;
                    case 5: case 6: in.getLong(); i++; break;
                    case 7: case 8: case 16: case 19: case 20: r1[i] = in.getShort() & 0xffff; break;
                    case 9: case 10: case 11: case 12: case 17: case 18:
                        r1[i] = in.getShort() & 0xffff; r2[i] = in.getShort() & 0xffff; break;
                    case 15: in.get(); r1[i] = in.getShort() & 0xffff; break;
                    default: throw new IOException("unknown constant pool tag " + t);
                }
            }
            end = in.position();
        }
    }

    static void skipAttributes(ByteBuffer in) {
        int a = in.getShort() & 0xffff;
        for (int j = 0; j < a; j++) { in.getShort(); int len = in.getInt(); in.position(in.position() + len); }
    }

    static void writeHead(DataOutputStream o, byte[] b, Pool p, int added) throws IOException {
        o.write(b, 0, p.countPos);
        o.writeShort(p.count + added);
        o.write(b, p.countPos + 2, p.end - p.countPos - 2);
    }

    // ---- name-hash: add hashCode() from the final String name field ----------------------------------------------
    static byte[] patchHashCode(byte[] b) throws IOException {
        ByteBuffer in = ByteBuffer.wrap(b);
        Pool p = new Pool(in);
        in.getShort();
        int thisClass = in.getShort() & 0xffff;
        in.getShort();
        int ifaces = in.getShort() & 0xffff;
        for (int i = 0; i < ifaces; i++) in.getShort();
        boolean hasName = false;
        int fields = in.getShort() & 0xffff;
        for (int i = 0; i < fields; i++) {
            int acc = in.getShort() & 0xffff;
            String fn = p.utf[in.getShort() & 0xffff], fd = p.utf[in.getShort() & 0xffff];
            if ("name".equals(fn) && "Ljava/lang/String;".equals(fd) && (acc & 0x0018) == 0x0010) hasName = true;
            skipAttributes(in);
        }
        if (!hasName) throw new IOException("no final instance field 'String name'");
        int methodsCountPos = in.position();
        int methods = in.getShort() & 0xffff;
        for (int i = 0; i < methods; i++) {
            in.getShort();
            String mn = p.utf[in.getShort() & 0xffff], md = p.utf[in.getShort() & 0xffff];
            if ("hashCode".equals(mn) && "()I".equals(md)) return null;
            skipAttributes(in);
        }
        int methodsEnd = in.position();
        ByteArrayOutputStream bo = new ByteArrayOutputStream(b.length + 256);
        DataOutputStream o = new DataOutputStream(bo);
        int k = p.count;  // the first new constant pool index
        writeHead(o, b, p, 12);
        o.writeByte(1); o.writeUTF("hashCode");                             // k+0
        o.writeByte(1); o.writeUTF("()I");                                  // k+1
        o.writeByte(1); o.writeUTF("name");                                 // k+2
        o.writeByte(1); o.writeUTF("Ljava/lang/String;");                   // k+3
        o.writeByte(12); o.writeShort(k + 2); o.writeShort(k + 3);          // k+4  NameAndType name
        o.writeByte(9); o.writeShort(thisClass); o.writeShort(k + 4);       // k+5  Fieldref this.name
        o.writeByte(1); o.writeUTF("java/util/Objects");                    // k+6
        o.writeByte(7); o.writeShort(k + 6);                                // k+7  Class Objects
        o.writeByte(1); o.writeUTF("(Ljava/lang/Object;)I");                // k+8
        o.writeByte(12); o.writeShort(k); o.writeShort(k + 8);              // k+9  NameAndType hashCode
        o.writeByte(10); o.writeShort(k + 7); o.writeShort(k + 9);          // k+10 Methodref Objects.hashCode
        o.writeByte(1); o.writeUTF("Code");                                 // k+11
        o.write(b, p.end, methodsCountPos - p.end);
        o.writeShort(methods + 1);
        o.write(b, methodsCountPos + 2, methodsEnd - methodsCountPos - 2);
        // public int hashCode() { return java.util.Objects.hashCode(this.name); }  straight-line: no StackMapTable
        byte[] code = {0x2a, (byte) 0xb4, (byte) ((k + 5) >> 8), (byte) (k + 5),
                       (byte) 0xb8, (byte) ((k + 10) >> 8), (byte) (k + 10), (byte) 0xac};
        o.writeShort(0x0001); o.writeShort(k); o.writeShort(k + 1); o.writeShort(1);
        o.writeShort(k + 11); o.writeInt(12 + code.length);
        o.writeShort(1); o.writeShort(1); o.writeInt(code.length); o.write(code);
        o.writeShort(0); o.writeShort(0);
        o.write(b, methodsEnd, b.length - methodsEnd);
        o.flush();
        return bo.toByteArray();
    }

    // ---- call-site rewrite: invokevirtual owner.name:desc -> invokestatic SELF.helper:(Lowner;args)ret ------------
    static byte[] rewriteCalls(byte[] b, List<String[]> rules) throws IOException {
        ByteBuffer in = ByteBuffer.wrap(b);
        Pool p = new Pool(in);
        Map<Integer, String[]> hit = new LinkedHashMap<>();
        for (int i = 1; i < p.count; i++) {
            if (p.tag[i] != 10) continue;
            String owner = p.utf[p.r1[p.r1[i]]];
            int nat = p.r2[i];
            String mn = p.utf[p.r1[nat]], md = p.utf[p.r2[nat]];
            for (String[] r : rules) if (r[0].equals(owner) && r[1].equals(mn) && r[2].equals(md)) { hit.put(i, r); break; }
        }
        if (hit.isEmpty()) return null;
        int codeName = 0;
        for (int i = 1; i < p.count; i++) if (p.tag[i] == 1 && "Code".equals(p.utf[i])) { codeName = i; break; }
        if (codeName == 0) return null;
        // find every invokevirtual of a hit Methodref
        in.getShort(); in.getShort(); in.getShort();
        int ifaces = in.getShort() & 0xffff;
        for (int i = 0; i < ifaces; i++) in.getShort();
        int fields = in.getShort() & 0xffff;
        for (int i = 0; i < fields; i++) { in.getShort(); in.getShort(); in.getShort(); skipAttributes(in); }
        List<int[]> sites = new ArrayList<>();  // {offset of the opcode in b, old Methodref index}
        int methods = in.getShort() & 0xffff;
        for (int i = 0; i < methods; i++) {
            in.getShort(); in.getShort(); in.getShort();
            int attrs = in.getShort() & 0xffff;
            for (int j = 0; j < attrs; j++) {
                int an = in.getShort() & 0xffff;
                int len = in.getInt();
                int start = in.position();
                if (an == codeName) {
                    int codeLen = in.getInt(start + 4);
                    int code = start + 8;
                    scan(b, code, codeLen, hit, sites);
                }
                in.position(start + len);
            }
        }
        if (sites.isEmpty()) return null;
        // new constant pool entries: SELF's Class, and one Methodref per rule that is used
        Map<String, Integer> helperIdx = new LinkedHashMap<>();
        ByteArrayOutputStream cpb = new ByteArrayOutputStream();
        DataOutputStream cp = new DataOutputStream(cpb);
        int next = p.count;
        cp.writeByte(1); cp.writeUTF(SELF); int selfUtf = next++;
        cp.writeByte(7); cp.writeShort(selfUtf); int selfCls = next++;
        Map<Integer, Integer> remap = new LinkedHashMap<>();
        for (int[] s : sites) {
            String[] r = hit.get(s[1]);
            Integer m = helperIdx.get(r[3]);
            if (m == null) {
                String desc = "(L" + r[0] + ";" + r[2].substring(1);
                cp.writeByte(1); cp.writeUTF(r[3]); int nU = next++;
                cp.writeByte(1); cp.writeUTF(desc); int dU = next++;
                cp.writeByte(12); cp.writeShort(nU); cp.writeShort(dU); int nat = next++;
                cp.writeByte(10); cp.writeShort(selfCls); cp.writeShort(nat); m = next++;
                helperIdx.put(r[3], m);
            }
            remap.put(s[1], m);
        }
        if (next > 0xffff) throw new IOException("constant pool overflow");
        byte[] tail = Arrays.copyOfRange(b, p.end, b.length);
        for (int[] s : sites) {
            int at = s[0] - p.end;
            int m = remap.get(s[1]);
            tail[at] = (byte) 0xb8;
            tail[at + 1] = (byte) (m >> 8);
            tail[at + 2] = (byte) m;
        }
        ByteArrayOutputStream bo = new ByteArrayOutputStream(b.length + cpb.size());
        DataOutputStream o = new DataOutputStream(bo);
        writeHead(o, b, p, next - p.count);
        o.write(cpb.toByteArray());
        o.write(tail);
        o.flush();
        return bo.toByteArray();
    }

    // walk one method's bytecode; record invokevirtual sites that call a hit Methodref
    static void scan(byte[] b, int code, int len, Map<Integer, String[]> hit, List<int[]> sites) throws IOException {
        int pc = 0;
        while (pc < len) {
            int op = b[code + pc] & 0xff;
            int n;
            if (op == 0xb6) {
                int idx = ((b[code + pc + 1] & 0xff) << 8) | (b[code + pc + 2] & 0xff);
                if (hit.containsKey(idx)) sites.add(new int[]{code + pc, idx});
                n = 3;
            } else if (op == 0xaa) {
                int pad = (4 - ((pc + 1) % 4)) % 4;
                int at = code + pc + 1 + pad;
                int lo = ByteBuffer.wrap(b, at + 4, 4).getInt(), hi = ByteBuffer.wrap(b, at + 8, 4).getInt();
                n = 1 + pad + 12 + 4 * (hi - lo + 1);
            } else if (op == 0xab) {
                int pad = (4 - ((pc + 1) % 4)) % 4;
                int at = code + pc + 1 + pad;
                int pairs = ByteBuffer.wrap(b, at + 4, 4).getInt();
                n = 1 + pad + 8 + 8 * pairs;
            } else if (op == 0xc4) {
                n = (b[code + pc + 1] & 0xff) == 0x84 ? 6 : 4;
            } else {
                n = LEN[op];
                if (n == 0) throw new IOException("unknown opcode " + op + " at " + pc);
            }
            pc += n;
        }
        if (pc != len) throw new IOException("bytecode walk ended at " + pc + ", not " + len);
    }

    static final int[] LEN = new int[256];
    static {
        for (int i = 0x00; i <= 0xc9; i++) LEN[i] = 1;
        LEN[0x10] = 2; LEN[0x11] = 3; LEN[0x12] = 2; LEN[0x13] = 3; LEN[0x14] = 3;
        for (int i = 0x15; i <= 0x19; i++) LEN[i] = 2;
        for (int i = 0x36; i <= 0x3a; i++) LEN[i] = 2;
        LEN[0x84] = 3;
        for (int i = 0x99; i <= 0xa8; i++) LEN[i] = 3;
        LEN[0xa9] = 2;
        LEN[0xaa] = 0; LEN[0xab] = 0;  // switches: computed
        for (int i = 0xb2; i <= 0xb8; i++) LEN[i] = 3;
        LEN[0xb9] = 5; LEN[0xba] = 5; LEN[0xbb] = 3; LEN[0xbc] = 2; LEN[0xbd] = 3;
        LEN[0xc0] = 3; LEN[0xc1] = 3; LEN[0xc4] = 0; LEN[0xc5] = 4; LEN[0xc6] = 3; LEN[0xc7] = 3;
        LEN[0xc8] = 5; LEN[0xc9] = 5;
    }
}
"""


def vkey(v):
    return [int(x) for x in re.findall(r"\d+", v or "")]


def _skip(t, i):
    """If t[i] opens a comment, string or char literal, the index just past it; else None."""
    n = len(t)
    c = t[i]
    if c == ";":
        j = t.find("\n", i)
        return n if j < 0 else j
    if c == '"':
        i += 1
        while i < n and t[i] != '"':
            i += 2 if t[i] == "\\" else 1
        return i + 1
    if c == "\\":
        return i + 2
    return None


def scan_map(t, start):
    """Index just past the bracket closing the form whose opener is at start."""
    depth, i, n = 0, start, len(t)
    while i < n:
        s = _skip(t, i)
        if s is not None:
            i = s
            continue
        c = t[i]
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    sys.exit("kitforge-cljdeps: unbalanced form in deps.edn")


def deps_span(t):
    """(open, close) of the project's top-level :deps map: the :deps key of the first form, at depth 1."""
    depth, i, n = 0, 0, len(t)
    while i < n:
        s = _skip(t, i)
        if s is not None:
            i = s
            continue
        c = t[i]
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
        elif depth == 1 and t.startswith(":deps", i) and not re.match(r"[\w./*+!?-]", t[i + 5:i + 6] or " "):
            j = i + 5
            while j < n:
                s = _skip(t, j)
                if s is not None and t[j] == ";":
                    j = s
                    continue
                if t[j] == "{":
                    return j, scan_map(t, j)
                if not (t[j].isspace() or t[j] == ","):
                    break
                j += 1
            sys.exit("kitforge-cljdeps: the top-level :deps value is not a map")
        i += 1
    sys.exit("kitforge-cljdeps: no top-level :deps map in deps.edn")


def top_keys(t, o, c):
    """{lib symbol: (value open, value close)} for the entries of the map spanning t[o:c]."""
    keys, i, expect_key, key = {}, o + 1, True, None
    while i < c - 1:
        s = _skip(t, i)
        if s is not None:
            i = s
            continue
        ch = t[i]
        if ch.isspace() or ch == ",":
            i += 1
            continue
        if t.startswith("#_", i):  # reader discard: the next form is not part of the map
            i += 2
            while i < c - 1 and (t[i].isspace() or t[i] == ","):
                i += 1
            if i < c - 1 and t[i] in "{[(":
                i = scan_map(t, i)
            else:
                i += len(re.match(r"[^\s,{}\[\]()\";]*", t[i:]).group(0)) or 1
            continue
        if ch in "{[(":
            end = scan_map(t, i)
            if not expect_key and key is not None:
                keys[key] = (i, end)
            expect_key, key, i = not expect_key, None, end
            continue
        m = re.match(r"[^\s,{}\[\]()\";]+", t[i:])
        tok = m.group(0)
        if expect_key:
            key = tok
        expect_key, i = not expect_key, i + len(tok)
    return keys


def inject(path, pins):
    t = open(path).read()
    adds = []
    for lib, ver in pins:
        o, c = deps_span(t)
        keys = top_keys(t, o, c)
        if lib in keys:
            vo, vc = keys[lib]
            val = t[vo:vc]
            vm = re.search(r':mvn/version\s+"([^"]*)"', val)
            if not vm:
                sys.exit(f"kitforge-cljdeps: {lib} is a top-level dep without :mvn/version; raise it by hand")
            if vkey(vm.group(1)) >= vkey(ver):
                print(f"kitforge-cljdeps: {lib} already {vm.group(1)} (>= {ver})")
                continue
            t = t[:vo] + val[:vm.start(1)] + ver + val[vm.end(1):] + t[vc:]
            print(f"kitforge-cljdeps: {lib} {vm.group(1)} -> {ver} (top-level, raised in place)")
        else:
            adds.append(f'{lib} {{:mvn/version "{ver}"}} ; ReadyStack CVE floor (strategy dep_bumps)\n  ')
            print(f"kitforge-cljdeps: {lib} -> {ver} (added as a top-level dep)")
    if adds:
        o, c = deps_span(t)
        t = t[:o + 1] + "".join(adds) + t[o + 1:]
    o, c = deps_span(t)  # the edited file must still read as one top-level :deps map holding every pin
    keys = top_keys(t, o, c)
    missing = [lib for lib, _ in pins if lib not in keys]
    if missing:
        sys.exit(f"kitforge-cljdeps: after the edit {missing} are not top-level deps")
    open(path, "w").write(t)


def jars(d):
    for root, dirs, files in os.walk(d):
        dirs.sort()
        for f in sorted(files):
            if f.endswith(".jar"):
                yield os.path.join(root, f)


def verify(d, pins):
    bad, seen = [], {lib: [] for lib, _ in pins}
    for j in jars(d):
        with zipfile.ZipFile(j) as z:
            names = set(z.namelist())
            for lib, ver in pins:
                g, a = lib.split("/", 1)
                name = f"META-INF/maven/{g}/{a}/pom.properties"
                if name in names:
                    props = dict(l.split("=", 1) for l in z.read(name).decode("utf-8", "replace").splitlines()
                                 if "=" in l and not l.startswith("#"))
                    got = props.get("version", "").strip()
                    seen[lib].append(got)
                    if vkey(got) < vkey(ver):
                        bad.append(f"{os.path.basename(j)}: {lib} {got} < {ver}")
    for lib, vs in seen.items():
        print(f"kitforge-cljdeps: {lib} in the built jars: {', '.join(vs) or 'NOT PRESENT (the bump has no effect)'}")
    if bad:
        sys.exit("kitforge-cljdeps: dep_bumps did not take: " + "; ".join(bad))


def normalize(d, epoch):
    base = max(int(epoch), 315532800)
    base -= base % 2
    dt = time.gmtime(base)[:6]
    # Clojure's RT.load compiles a namespace from its .clj/.cljc source instead of loading its AOT classes when the
    # source entry is not OLDER than the class entry. One timestamp for every entry makes them equal, so every
    # namespace is re-evaluated from source in a different order than the AOT build used and Metabase v0.64.2 died
    # at boot with a malli :ref to a namespace that had not registered yet (chain 543, 2026-10-16; the same jar
    # without normalisation boots). Classes get the next DOS-time tick (2 s), so classes stay newer, as built.
    dt_class = time.gmtime(base + 2)[:6]
    for j in jars(d):
        tmp = j + ".norm"
        with zipfile.ZipFile(j) as zi, zipfile.ZipFile(tmp, "w") as zo:
            by = {i.filename: i for i in zi.infolist()}
            first = [n for n in ("META-INF/", "META-INF/MANIFEST.MF") if n in by]
            order = first + sorted(n for n in by if n not in first)
            for name in order:
                src = by[name]
                zinfo = zipfile.ZipInfo(name, date_time=dt_class if name.endswith(".class") else dt)
                zinfo.compress_type = src.compress_type
                zinfo.external_attr = src.external_attr
                zinfo.create_system = 3
                zo.writestr(zinfo, zi.read(name))
        os.replace(tmp, j)
        print(f"kitforge-cljdeps: normalized {j} ({len(order)} entries)")


_TOKEN = re.compile(r"[^\s,{}\[\]()\";]+")


def _ws(t, i, c):
    """Index of the next form start at or after i (skips whitespace, commas, comments and #_ discards)."""
    while i < c:
        if t[i].isspace() or t[i] == ",":
            i += 1
        elif t[i] == ";":
            i = _skip(t, i)
        elif t.startswith("#_", i):
            i = form_end(t, _ws(t, i + 2, c), c)
        else:
            break
    return i


def form_end(t, i, c):
    """Index just past the one EDN form starting at t[i] (collections, #{} #() #?() #"" #tag x, 'x, ^m x)."""
    ch = t[i]
    if ch in "{[(":
        return scan_map(t, i)
    if ch in '";\\':
        return _skip(t, i)
    if ch in "'`~@":
        return form_end(t, _ws(t, i + 1, c), c)
    if ch == "^":
        return form_end(t, _ws(t, form_end(t, _ws(t, i + 1, c), c), c), c)
    if ch == "#":
        nx = t[i + 1:i + 2]
        if nx in ("{", "("):
            return scan_map(t, i + 1)
        if nx == '"':
            return _skip(t, i + 1)
        if nx == "?":
            return scan_map(t, i + 3 if t.startswith("#?@", i) else i + 2)
        if nx == "'":
            return form_end(t, i + 2, c)
        if nx == "#":
            return i + len(_TOKEN.match(t, i).group(0))
        tag = _TOKEN.match(t, i + 1)  # tagged literal: #tag form
        return form_end(t, _ws(t, i + 1 + len(tag.group(0)), c), c) if tag else i + 1
    m = _TOKEN.match(t, i)
    return i + (len(m.group(0)) if m else 1)


def entries(t, o, c):
    """{key text: (value start, value end)} for the map literal spanning t[o:c] (t[o] is its '{')."""
    out, i = {}, _ws(t, o + 1, c - 1)
    while i < c - 1:
        ke = form_end(t, i, c)
        vs = _ws(t, ke, c - 1)
        if vs >= c - 1:
            sys.exit(f"kitforge-cljdeps: map entry {t[i:ke]!r} has no value")
        ve = form_end(t, vs, c)
        out[t[i:ke]] = (vs, ve)
        i = _ws(t, ve, c - 1)
    return out


def hashagent(jar, quiet=False):
    """Compile AGENT_JAVA with the build JDK's javac into a -javaagent jar (fixed entry stamps, sorted entries)."""
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "KitforgeNameHash.java")
        with open(src, "w") as f:
            f.write(AGENT_JAVA)
        out = os.path.join(td, "classes")
        os.makedirs(out)
        try:
            subprocess.run(["javac", "-nowarn", "-d", out, src], check=True)
        except (OSError, subprocess.CalledProcessError) as e:
            sys.exit(f"kitforge-cljdeps: cannot compile the name-hash agent ({e}); the builder image must be a JDK")
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(zipfile.ZipInfo("META-INF/MANIFEST.MF", date_time=(1980, 1, 1, 0, 0, 0)),
                       "Manifest-Version: 1.0\nPremain-Class: KitforgeNameHash\n")
            for name in sorted(os.listdir(out)):
                with open(os.path.join(out, name), "rb") as f:
                    z.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), f.read())
    if not quiet:
        print(f"kitforge-cljdeps: wrote {jar}")


def shadowdet(path, jar):
    """See SHADOW_NOTE: serial builds plus the JSChunk name-hash agent for every build in the shadow-cljs config."""
    if not os.path.exists(path):
        print(f"kitforge-cljdeps: no {path}; nothing to make reproducible")
        return
    opts = ["-XX:+UnlockExperimentalVMOptions", "-XX:hashCode=5", f"-javaagent:{jar}={SHADOW_AGENT_TARGETS}"]
    t = open(path).read()

    def builds_of(t):
        top = _ws(t, 0, len(t))
        if t[top:top + 1] != "{":
            sys.exit(f"kitforge-cljdeps: {path} is not a map")
        root = (top, scan_map(t, top))
        b = entries(t, *root).get(":builds")
        if not b or t[b[0]] != "{":
            sys.exit(f"kitforge-cljdeps: {path} has no :builds map")
        bs = {k: v for k, v in entries(t, *b).items() if t[v[0]] == "{"}
        if not bs:
            sys.exit(f"kitforge-cljdeps: {path} :builds holds no build maps")
        return root, bs

    def parallel_build(t, ent):
        """(build-level :parallel-build span or None, :release-level span or None, build :compiler-options span)."""
        def pb_in(m):
            co = m.get(":compiler-options")
            if co is not None and t[co[0]] != "{":
                sys.exit(f"kitforge-cljdeps: {path}: a :compiler-options is not a map literal")
            return (entries(t, *co).get(":parallel-build") if co else None), co
        pb, co = pb_in(ent)
        rel = ent.get(":release")  # release-mode overrides win over the build's own compiler options
        rpb = pb_in(entries(t, *rel))[0] if rel and t[rel[0]] == "{" else None
        return pb, rpb, co

    root, builds = builds_of(t)
    edits = []
    for bid, (bo, bc) in builds.items():
        pb, rpb, co = parallel_build(t, entries(t, bo, bc))
        if pb:
            edits.append((pb[0], pb[1], "false"))
        elif co:
            edits.append((co[0] + 1, co[0] + 1, ":parallel-build false "))
        else:
            edits.append((bo + 1, bo + 1, ":compiler-options {:parallel-build false} "))
        if rpb:
            edits.append((rpb[0], rpb[1], "false"))
    jv = entries(t, *root).get(":jvm-opts")
    if jv is None:
        edits.append((root[0] + 1, root[0] + 1, ":jvm-opts [" + " ".join(f'"{o}"' for o in opts) + "]\n "))
    elif t[jv[0]] != "[":
        sys.exit(f"kitforge-cljdeps: {path} :jvm-opts is not a vector literal")
    else:
        have = t[jv[0]:jv[1]]
        add = [o for o in opts if f'"{o}"' not in have]
        if add:
            edits.append((jv[1] - 1, jv[1] - 1, " " + " ".join(f'"{o}"' for o in add)))
    for a, z, s in sorted(edits, reverse=True):
        t = t[:a] + s + t[z:]
    root, builds = builds_of(t)  # re-read what was written: fail closed if any build or option did not take
    for bid, (bo, bc) in builds.items():
        pb, rpb, _ = parallel_build(t, entries(t, bo, bc))
        if not pb or t[pb[0]:pb[1]] != "false" or (rpb and t[rpb[0]:rpb[1]] != "false"):
            sys.exit(f"kitforge-cljdeps: {bid} did not take :parallel-build false")
    have = t[slice(*entries(t, *root)[":jvm-opts"])]
    if not all(f'"{o}"' in have for o in opts):
        sys.exit(f"kitforge-cljdeps: {path} :jvm-opts did not take {opts}")
    open(path, "w").write(t)
    if not os.path.exists(jar):  # the kit builds it first (hashagent); a direct call builds it here
        hashagent(jar, quiet=True)
    print(f"kitforge-cljdeps: {path}: :parallel-build false in {', '.join(builds)}; :jvm-opts load {jar} "
          f"for {SHADOW_AGENT_TARGETS}")


def pins_of(args):
    out = []
    for a in args:
        lib, _, ver = a.partition("=")
        if "/" not in lib or not ver:
            sys.exit(f"kitforge-cljdeps: bad pin {a!r} (want group/artifact=version)")
        out.append((lib, ver))
    return out


if __name__ == "__main__":
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "inject":
        inject(rest[0], pins_of(rest[1:]))
    elif cmd == "verify":
        verify(rest[0], pins_of(rest[1:]))
    elif cmd == "normalize":
        normalize(rest[0], rest[1])
    elif cmd == "shadowdet":
        shadowdet(rest[0], rest[1])
    elif cmd == "hashagent":
        hashagent(rest[0])
    else:
        sys.exit(f"kitforge-cljdeps: unknown command {cmd!r}")
