package fr.bagyette.aternauto.neoforge.compat.v26_1_1;

import fr.bagyette.aternauto.common.ClientUserAgent;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLPaths;

@Mod("aternauto")
public final class AternAutoMod {
  public AternAutoMod() {
    ClientUserAgent.configure(FMLPaths.CONFIGDIR.get().resolve("aternauto"));
  }
}
