function initializeCoreMod() {
    var ASMAPI = Java.type('net.minecraftforge.coremod.api.ASMAPI');
    var Opcodes = Java.type('org.objectweb.asm.Opcodes');
    var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
    var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
    var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
    var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
    var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');
    var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
    var FrameNode = Java.type('org.objectweb.asm.tree.FrameNode');
    return {
        aternauto_connect: {
            target: {
                type: 'METHOD',
                class: 'net.minecraft.client.gui.screen.ConnectingScreen',
                methodName: ASMAPI.mapMethod('func_146367_a'),
                methodDesc: '(Ljava/lang/String;I)V'
            },
            transformer: function(method) {
                var hook = new InsnList();
                var resume = new LabelNode();
                hook.add(new VarInsnNode(Opcodes.ALOAD, 0));
                hook.add(new VarInsnNode(Opcodes.ALOAD, 1));
                hook.add(new VarInsnNode(Opcodes.ILOAD, 2));
                hook.add(new MethodInsnNode(Opcodes.INVOKESTATIC,
                    'fr/bagyette/aternauto/forge/compat/v1_14_4/ForgeHooks', 'defer',
                    '(Ljava/lang/Object;Ljava/lang/String;I)Z', false));
                hook.add(new JumpInsnNode(Opcodes.IFEQ, resume));
                hook.add(new InsnNode(Opcodes.RETURN));
                hook.add(resume);
                hook.add(new FrameNode(Opcodes.F_SAME, 0, null, 0, null));
                method.instructions.insert(hook);
                method.maxStack = Math.max(method.maxStack, 3);
                return method;
            }
        }
    };
}
