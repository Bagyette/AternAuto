package fr.bagyette.aternauto.fabric;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import fr.bagyette.aternauto.common.ClientUserAgent;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import net.fabricmc.loader.api.FabricLoader;
import org.objectweb.asm.tree.ClassNode;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;

/** Loads only the Minecraft adapter matching the running instance. */
public final class AdapterPlugin implements IMixinConfigPlugin {
  private List<String> mixins;

  @Override
  public void onLoad(String mixinPackage) {
    ClientUserAgent.configure(FabricLoader.getInstance().getConfigDir().resolve("aternauto"));
    String version =
        FabricLoader.getInstance()
            .getModContainer("minecraft")
            .get()
            .getMetadata()
            .getVersion()
            .getFriendlyString();
    try (InputStreamReader reader =
        new InputStreamReader(
            AdapterPlugin.class.getResourceAsStream("/aternauto-adapters.json"),
            StandardCharsets.UTF_8)) {
      JsonObject index = new JsonParser().parse(reader).getAsJsonObject();
      JsonObject adapter = index.getAsJsonObject(version);
      if (adapter == null) {
        throw new IllegalStateException(
            "AternAuto: version Minecraft non prise en charge: " + version);
      }
      String prefix = adapter.get("package").getAsString();
      mixins = new ArrayList<>();
      mixins.add(prefix + ".ConnectionMixin");
      mixins.add(prefix + ".DisconnectedScreenMixin");
      mixins.add(prefix + ".RetryClientMixin");
      mixins.add(prefix + ".ScreenChangeMixin");
      mixins.add(prefix + ".ReportDisconnectedMixin");
      if (adapter.get("legacy").getAsBoolean()) {
        mixins.add(prefix + ".ClientTickMixin");
      }
    } catch (java.io.IOException e) {
      throw new IllegalStateException("AternAuto: index des adaptateurs illisible", e);
    }
  }

  @Override
  public String getRefMapperConfig() {
    return null;
  }

  @Override
  public boolean shouldApplyMixin(String targetClassName, String mixinClassName) {
    return true;
  }

  @Override
  public void acceptTargets(Set<String> myTargets, Set<String> otherTargets) {}

  @Override
  public List<String> getMixins() {
    return mixins;
  }

  @Override
  public void preApply(
      String targetClassName, ClassNode targetClass, String mixinClassName, IMixinInfo mixinInfo) {}

  @Override
  public void postApply(
      String targetClassName, ClassNode targetClass, String mixinClassName, IMixinInfo mixinInfo) {}
}
