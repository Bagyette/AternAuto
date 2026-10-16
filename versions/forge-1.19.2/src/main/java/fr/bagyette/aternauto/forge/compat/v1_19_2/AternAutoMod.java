package fr.bagyette.aternauto.forge.compat.v1_19_2;

import fr.bagyette.aternauto.common.ClientUserAgent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLPaths;

@Mod("aternauto")
public final class AternAutoMod {
  public AternAutoMod() {
    ClientUserAgent.configure(FMLPaths.CONFIGDIR.get().resolve("aternauto"));
  }
}
