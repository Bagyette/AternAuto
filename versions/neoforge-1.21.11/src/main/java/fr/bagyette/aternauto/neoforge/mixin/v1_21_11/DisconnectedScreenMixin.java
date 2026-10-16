package fr.bagyette.aternauto.neoforge.mixin.v1_21_11;

import net.minecraft.client.gui.screens.DisconnectedScreen;
import net.minecraft.network.DisconnectionDetails;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(DisconnectedScreen.class)
public interface DisconnectedScreenMixin {
  @Accessor("details")
  DisconnectionDetails aternauto$getReason();
}
