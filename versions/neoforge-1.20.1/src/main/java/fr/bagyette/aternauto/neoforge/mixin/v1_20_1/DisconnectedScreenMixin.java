package fr.bagyette.aternauto.neoforge.mixin.v1_20_1;

import net.minecraft.client.gui.screens.DisconnectedScreen;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(DisconnectedScreen.class)
public interface DisconnectedScreenMixin {
  @Accessor("reason")
  Component aternauto$getReason();
}
