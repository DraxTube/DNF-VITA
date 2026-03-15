"""
Patch sdlayer.cpp for PS Vita DNF 2001 port - Performance optimizations.

STRATEGY:
  - Resize fb_texture and gpu_texture to 320x200 (Duke3D native resolution)
  - Engine renders at 320x200 directly into fb_texture
  - videoShowFrame uses vita2d_draw_texture_scale(3.0, 2.72) to fill 960x544
  - LINEAR filter already set on gpu_texture for smooth upscale
  - NO frame limiter — let the engine run as fast as possible
  - vita2d_set_vblank_wait(0) already set in psp2_main = uncapped FPS

WHY 320x200:
  - Duke3D native resolution, 75% fewer pixels than 640x400
  - 960/320 = 3.0x, 544/200 = 2.72x clean GPU upscale
  - Maximum performance boost for smooth gameplay
"""
import sys


def patch_performance(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    if 'DNF_PERF_PATCH_APPLIED' in content:
        print(f"  {filepath} already patched, skipping.")
        return

    changes = 0

    # =========================================================================
    # PATCH 1: Guard marker
    # =========================================================================
    old = 'vita2d_texture *fb_texture, *gpu_texture;'
    new = 'vita2d_texture *fb_texture, *gpu_texture; // DNF_PERF_PATCH_APPLIED'
    if old in content:
        content = content.replace(old, new, 1)
        changes += 1
        print("    [OK] Guard marker added")
    else:
        print("    [FAIL] vita2d globals line not found!")

    # =========================================================================
    # PATCH 2: Resize gpu_texture from 960x544 to 320x200
    # =========================================================================
    old = '    gpu_texture = vita2d_create_empty_texture_format(960, 544, SCE_GXM_TEXTURE_FORMAT_P8_1BGR);\n'
    new = '    gpu_texture = vita2d_create_empty_texture_format(320, 200, SCE_GXM_TEXTURE_FORMAT_P8_1BGR); // DNF: 320x200\n'
    if old in content:
        content = content.replace(old, new, 1)
        changes += 1
        print("    [OK] gpu_texture resized to 320x200")
    else:
        print("    [FAIL] gpu_texture 960x544 creation not found!")

    # =========================================================================
    # PATCH 3: Resize fb_texture from 960x544 to 320x200
    # =========================================================================
    old = '    fb_texture = vita2d_create_empty_texture_format(960, 544, SCE_GXM_TEXTURE_FORMAT_P8_1BGR);\n'
    new = '    fb_texture = vita2d_create_empty_texture_format(320, 200, SCE_GXM_TEXTURE_FORMAT_P8_1BGR); // DNF: 320x200\n'
    if old in content:
        content = content.replace(old, new, 1)
        changes += 1
        print("    [OK] fb_texture resized to 320x200")
    else:
        print("    [FAIL] fb_texture 960x544 creation not found!")

    # =========================================================================
    # PATCH 4: Replace videoShowFrame draw call with scaled version
    # scale_x = 960/320 = 3.0, scale_y = 544/200 = 2.72
    # NO frame limiter — run as fast as possible for best FPS
    # =========================================================================
    old = (
        '    memcpy(vita2d_texture_get_datap(gpu_texture),'
        'vita2d_texture_get_datap(fb_texture),'
        'vita2d_texture_get_stride(gpu_texture)*vita2d_texture_get_height(gpu_texture));\n'
        '    vita2d_start_drawing();\n'
        '    vita2d_draw_texture(gpu_texture, 0, 0);\n'
        '    vita2d_end_drawing();\n'
        '    vita2d_wait_rendering_done();\n'
        '    vita2d_swap_buffers();'
    )
    new = (
        '    memcpy(vita2d_texture_get_datap(gpu_texture),'
        'vita2d_texture_get_datap(fb_texture),'
        'vita2d_texture_get_stride(gpu_texture)*vita2d_texture_get_height(gpu_texture));\n'
        '    vita2d_start_drawing();\n'
        '    vita2d_draw_texture_scale(gpu_texture, 0, 0, 3.0f, 2.72f); // DNF: 320x200 -> 960x544\n'
        '    vita2d_end_drawing();\n'
        '    vita2d_wait_rendering_done();\n'
        '    vita2d_swap_buffers();'
    )
    if old in content:
        content = content.replace(old, new, 1)
        changes += 1
        print("    [OK] videoShowFrame: scaled 320x200 -> 960x544, no fps cap")
    else:
        print("    [SKIP] videoShowFrame pattern not found (non-fatal)")

    # =========================================================================
    # PATCH 5: Resolution guard in videoBeginDrawing
    # =========================================================================
    old = '\tframeplace = (intptr_t)framebuffer;'
    new = (
        '\tframeplace = (intptr_t)framebuffer;\n'
        '#ifdef __PSP2__\n'
        '\t// DNF_VITA_RESOLUTION_GUARD: Force 320x200 every frame.\n'
        '\t// Prevents config/engine from overriding resolution after videoSetMode.\n'
        '\txdim = 320;\n'
        '\tydim = 200;\n'
        '\tbytesperline = 320;\n'
        '#endif'
    )
    if old in content:
        content = content.replace(old, new, 1)
        changes += 1
        print("    [OK] videoBeginDrawing: resolution guard added")
    else:
        print("    [SKIP] videoBeginDrawing pattern not found (non-fatal)")

    if changes < 3:
        print(f"  ERROR: Only {changes} critical changes applied!")
        sys.exit(1)

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"\n  Patched: {changes} changes applied")
    print(f"    fb/gpu textures: 320x200")
    print(f"    Engine renders at 320x200, scales 3.0x/2.72x to fill 960x544")
    print(f"    No frame limiter - maximum FPS")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path_to_sdlayer.cpp>")
        sys.exit(1)

    patch_performance(sys.argv[1])
