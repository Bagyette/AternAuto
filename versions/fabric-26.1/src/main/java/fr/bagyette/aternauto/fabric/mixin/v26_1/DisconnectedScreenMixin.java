package fr.bagyette.aternauto.fabric.mixin.v26_1;

import net.minecraft.client.gui.screens.DisconnectedScreen;
import net.minecraft.network.DisconnectionDetails;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(DisconnectedScreen.class)
public interface DisconnectedScreenMixin {
  @Accessor("details")
  DisconnectionDetails aternauto$getReason();
}
