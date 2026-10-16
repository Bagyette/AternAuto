package fr.bagyette.aternauto.testing.smoke;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

/** Render and tick probes for LaunchWrapper clients, isolated from the released mod. */
public final class SmokeTransformer {
  private static final String CHECKS = "fr/bagyette/aternauto/testing/smoke/SmokeChecks";

  private SmokeTransformer() {}

  public static byte[] transform(String name, byte[] bytes) {
    if (bytes == null) {
      return null;
    }
    boolean client = "net.minecraft.client.Minecraft".equals(name);
    boolean screen = System.getProperty("smoke.screen").equals(name);
    if (!client && !screen) {
      return bytes;
    }
    ClassNode node = new ClassNode();
    new ClassReader(bytes).accept(node, 0);
    int patched = 0;
    for (MethodNode method : node.methods) {
      if (client && "func_71407_l".equals(method.name) && "()V".equals(method.desc)) {
        tail(method, "tick");
        patched++;
      }
      if (screen && "func_73863_a".equals(method.name) && "(IIF)V".equals(method.desc)) {
        tail(method, "rendered");
        patched++;
      }
    }
    if (patched != 1) {
      throw new IllegalStateException("Missing runtime probe method in " + name);
    }
    ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
    node.accept(writer);
    return writer.toByteArray();
  }

  private static void tail(MethodNode method, String hook) {
    for (AbstractInsnNode instruction = method.instructions.getFirst(); instruction != null; ) {
      AbstractInsnNode next = instruction.getNext();
      if (instruction.getOpcode() == Opcodes.RETURN) {
        InsnList probe = new InsnList();
        probe.add(new VarInsnNode(Opcodes.ALOAD, 0));
        probe.add(
            new MethodInsnNode(Opcodes.INVOKESTATIC, CHECKS, hook, "(Ljava/lang/Object;)V", false));
        method.instructions.insertBefore(instruction, probe);
      }
      instruction = next;
    }
  }
}
