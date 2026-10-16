package fr.bagyette.aternauto.forge.compat.v1_18_2;

import fr.bagyette.aternauto.common.FailureKind;
import fr.bagyette.aternauto.common.IssueReport;
import java.util.ArrayList;
import java.util.List;
import net.minecraftforge.fml.ModList;

public final class LoaderReports {
  private LoaderReports() {}

  public static IssueReport capture(String host, int port, FailureKind failure, int status) {
    List<IssueReport.Mod> mods = new ArrayList<>();
    String loaderVersion = "Unknown";
    for (var mod : ModList.get().getMods()) {
      if ("forge".equals(mod.getModId())) {
        loaderVersion = mod.getVersion().toString();
      }
      if (!"minecraft".equals(mod.getModId())
          && !"forge".equals(mod.getModId())
          && !"aternauto".equals(mod.getModId())) {
        mods.add(new IssueReport.Mod(mod.getDisplayName(), mod.getVersion().toString()));
      }
    }
    return new IssueReport("1.18.2", "Forge", loaderVersion, mods, host, port, failure, status);
  }
}
