package fr.bagyette.aternauto.fabric.mixin.v1_19_4;

import net.minecraft.client.gui.screen.DisconnectedScreen;
import net.minecraft.text.Text;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(DisconnectedScreen.class)
public interface DisconnectedScreenMixin {
  @Accessor("reason")
  Text aternauto$getReason();
}
