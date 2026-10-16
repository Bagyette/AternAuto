package fr.bagyette.aternauto.forge;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

import java.io.InputStream;
import java.nio.file.Path;
import java.util.zip.ZipFile;
import org.junit.jupiter.api.Test;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.analysis.Analyzer;
import org.objectweb.asm.tree.analysis.BasicVerifier;

class ForgeTransformerTest {
  @Test
  void injectsExactlyOneVerifiedHookIntoBothRealMinecraftClasses() throws Exception {
    for (String version : new String[] {"1.8.9", "1.12.2"}) {
      Path jar =
          Path.of(
              System.getProperty("aternauto.workspace"),
              ".tools",
              "minecraft-" + version + "-srg.jar");
      byte[] original;
      try (ZipFile archive = new ZipFile(jar.toFile());
          InputStream input =
              archive.getInputStream(
                  archive.getEntry("net/minecraft/client/multiplayer/GuiConnecting.class"))) {
        original = input.readAllBytes();
      }
      ConnectionTransformer transformer = new ConnectionTransformer();
      byte[] transformed =
          transformer.transform(
              "ignored", "net.minecraft.client.multiplayer.GuiConnecting", original);
      assertNotEquals(original.length, transformed.length);
      assertArrayEquals(
          transformed,
          transformer.transform(
              "ignored", "net.minecraft.client.multiplayer.GuiConnecting", transformed));
      ClassNode node = new ClassNode();
      new ClassReader(transformed).accept(node, ClassReader.EXPAND_FRAMES);
      int hooks = 0;
      for (Object item : node.methods) {
        MethodNode method = (MethodNode) item;
        new Analyzer(new BasicVerifier()).analyze(node.name, method);
        for (AbstractInsnNode instruction = method.instructions.getFirst();
            instruction != null;
            instruction = instruction.getNext()) {
          if (instruction instanceof MethodInsnNode call
              && call.name.equals("defer")
              && call.owner.equals("fr/bagyette/aternauto/forge/ForgeHooks")) {
            hooks++;
          }
        }
      }
      assertEquals(1, hooks);
    }
  }
}
