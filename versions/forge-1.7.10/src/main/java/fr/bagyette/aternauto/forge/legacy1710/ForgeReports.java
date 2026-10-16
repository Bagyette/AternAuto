package fr.bagyette.aternauto.forge.legacy1710;

import cpw.mods.fml.common.Loader;
import cpw.mods.fml.common.ModContainer;
import fr.bagyette.aternauto.common.FailureKind;
import fr.bagyette.aternauto.common.IssueReport;
import java.util.ArrayList;
import java.util.List;

/** Legacy Forge metadata bridge, shared by Minecraft 1.8.9 and 1.12.2. */
public final class ForgeReports {
  private ForgeReports() {}

  public static IssueReport capture(String host, int port, FailureKind error, int httpStatus) {
    List<IssueReport.Mod> mods = new ArrayList<>();
    String minecraft = "Unknown";
    String forge = "Unknown";
    for (ModContainer mod : Loader.instance().getModList()) {
      if (mod.getModId().equals("minecraft")) {
        minecraft = mod.getVersion();
      } else if (mod.getModId().equals("forge")) {
        forge = mod.getVersion();
      } else if (!mod.getModId().equals("aternauto")) {
        mods.add(new IssueReport.Mod(mod.getName(), mod.getVersion()));
      }
    }
    return new IssueReport(minecraft, "Forge", forge, mods, host, port, error, httpStatus);
  }
}
