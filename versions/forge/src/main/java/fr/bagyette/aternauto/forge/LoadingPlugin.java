package fr.bagyette.aternauto.forge;

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
  public void injectData(Map<String, Object> data) {}

  @Override
  public String getAccessTransformerClass() {
    return null;
  }
}
