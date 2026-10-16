package fr.bagyette.aternauto.forge.legacy1710;

import net.minecraft.launchwrapper.IClassTransformer;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.JumpInsnNode;
import org.objectweb.asm.tree.LabelNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

/** Defers the connection before vanilla starts its network thread. */
public final class ConnectionTransformer implements IClassTransformer {
  private static final String HOOKS =
      ConnectionTransformer.class.getPackage().getName().replace('.', '/') + "/ForgeHooks";

  @Override
  public byte[] transform(String name, String transformedName, byte[] bytes) {
    if (bytes == null
        || !"net.minecraft.client.multiplayer.GuiConnecting".equals(transformedName)) {
      return bytes;
    }
    ClassNode node = new ClassNode();
    new ClassReader(bytes).accept(node, 0);
    int injected = 0;
    for (Object item : node.methods) {
      MethodNode method = (MethodNode) item;
      if ((!"func_146367_a".equals(method.name) && !"connect".equals(method.name))
          || !"(Ljava/lang/String;I)V".equals(method.desc)) {
        continue;
      }
      // Ignore a repeated pass through the launcher's transformer chain.
      boolean alreadyInjected = false;
      for (AbstractInsnNode instruction = method.instructions.getFirst();
          instruction != null;
          instruction = instruction.getNext()) {
        if (instruction instanceof MethodInsnNode
            && HOOKS.equals(((MethodInsnNode) instruction).owner)) {
          alreadyInjected = true;
        }
      }
      if (alreadyInjected) {
        return bytes;
      }
      InsnList hook = new InsnList();
      LabelNode resume = new LabelNode();
      hook.add(new VarInsnNode(Opcodes.ALOAD, 0));
      hook.add(new VarInsnNode(Opcodes.ALOAD, 1));
      hook.add(new VarInsnNode(Opcodes.ILOAD, 2));
      hook.add(
          new MethodInsnNode(
              Opcodes.INVOKESTATIC,
              HOOKS,
              "defer",
              "(Ljava/lang/Object;Ljava/lang/String;I)Z",
              false));
      hook.add(new JumpInsnNode(Opcodes.IFEQ, resume));
      hook.add(new InsnNode(Opcodes.RETURN));
      hook.add(resume);
      method.instructions.insert(hook);
      injected++;
    }
    if (injected != 1) {
      throw new IllegalStateException("AternAuto: point de connexion Forge introuvable.");
    }
    // A straight-line entry hook leaves the existing method body and exception handlers unchanged.
    ClassWriter writer =
        new ClassWriter(ClassWriter.COMPUTE_MAXS | ClassWriter.COMPUTE_FRAMES) {
          @Override
          protected String getCommonSuperClass(String left, String right) {
            return "java/lang/Object";
          }
        };
    node.accept(writer);
    return writer.toByteArray();
  }
}
