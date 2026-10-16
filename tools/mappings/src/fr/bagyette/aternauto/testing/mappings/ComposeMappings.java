package fr.bagyette.aternauto.testing.mappings;

import java.nio.file.Paths;
import net.minecraftforge.srgutils.IMappingFile;

/** Composes Mojang-to-obfuscated and obfuscated-to-SRG mappings for production jars. */
public final class ComposeMappings {
  private ComposeMappings() {}

  public static void main(String[] args) throws Exception {
    if (args.length != 3) {
      throw new IllegalArgumentException("Expected Mojang mappings, MCP mappings and output");
    }
    IMappingFile mojang = IMappingFile.load(Paths.get(args[0]).toFile());
    IMappingFile mcp = IMappingFile.load(Paths.get(args[1]).toFile());
    mojang.chain(mcp).write(Paths.get(args[2]), IMappingFile.Format.SRG, false);
  }
}
