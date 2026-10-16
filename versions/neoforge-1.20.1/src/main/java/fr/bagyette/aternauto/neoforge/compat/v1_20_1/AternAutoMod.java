package fr.bagyette.aternauto.neoforge.compat.v1_20_1;

import fr.bagyette.aternauto.common.ClientUserAgent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLPaths;

@Mod("aternauto")
public final class AternAutoMod {
  public AternAutoMod() {
    ClientUserAgent.configure(FMLPaths.CONFIGDIR.get().resolve("aternauto"));
  }
}
