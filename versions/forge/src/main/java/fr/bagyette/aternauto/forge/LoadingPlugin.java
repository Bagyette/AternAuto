package fr.bagyette.aternauto.forge;

import fr.bagyette.aternauto.common.ClientUserAgent;
import java.io.File;
import java.util.Map;
import net.minecraftforge.fml.relauncher.IFMLLoadingPlugin;

@IFMLLoadingPlugin.Name("AternAuto")
@IFMLLoadingPlugin.SortingIndex(1001)
@IFMLLoadingPlugin.TransformerExclusions({"fr.bagyette.aternauto.forge.ConnectionTransformer"})
public final class LoadingPlugin implements IFMLLoadingPlugin {
  @Override
  public String[] getASMTransformerClass() {
    return new String[] {"fr.bagyette.aternauto.forge.ConnectionTransformer"};
  }

  @Override
  public String getModContainerClass() {
    return null;
  }

  @Override
  public String getSetupClass() {
    return null;
  }

  @Override
  public void injectData(Map<String, Object> data) {
    Object location = data.get("mcLocation");
    if (location instanceof File) {
      ClientUserAgent.configure(((File) location).toPath().resolve("config").resolve("aternauto"));
    }
  }

  @Override
  public String getAccessTransformerClass() {
    return null;
  }
}
