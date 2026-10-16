package fr.bagyette.aternauto.fabric;

import fr.bagyette.aternauto.common.FailureKind;
import fr.bagyette.aternauto.common.IssueReport;
import java.util.ArrayList;
import java.util.List;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.loader.api.ModContainer;

/** Reads metadata only; no JAR files, account sessions or game paths are inspected. */
public final class FabricReports {
  private FabricReports() {}

  public static IssueReport capture(String host, int port, FailureKind error, int httpStatus) {
    FabricLoader loader = FabricLoader.getInstance();
    List<IssueReport.Mod> mods = new ArrayList<>();
    for (ModContainer container : loader.getAllMods()) {
      String id = container.getMetadata().getId();
      if (!id.equals("minecraft")
          && !id.equals("fabricloader")
          && !id.equals("aternauto")
          && !id.equals("java")) {
        mods.add(
            new IssueReport.Mod(
                container.getMetadata().getName(),
                container.getMetadata().getVersion().getFriendlyString()));
      }
    }
    return new IssueReport(
        version(loader, "minecraft"),
        "Fabric",
        version(loader, "fabricloader"),
        mods,
        host,
        port,
        error,
        httpStatus);
  }

  private static String version(FabricLoader loader, String id) {
    return loader.getModContainer(id).get().getMetadata().getVersion().getFriendlyString();
  }
}
