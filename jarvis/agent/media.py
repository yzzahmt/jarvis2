"""Medya araçları: video (ffmpeg, kare hassasiyetinde), Blender (Python ile 3B model), görsel inceleme.
Fareyle uygulama kullanmaktan çok daha güvenilir: "resmi 12. saniyede sağ üste koy" tek komut.
ffmpeg venv'deki imageio-ffmpeg'den, Blender data/apps/Blender.app'ten (HDD), yoksa /Applications'tan."""
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .. import config
from .tools import I, S, clip, tool

_BLENDERS = [config.path("data/apps/Blender.app/Contents/MacOS/Blender"),
             Path("/Applications/Blender.app/Contents/MacOS/Blender")]
BLENDER = next((b for b in _BLENDERS if b.exists()), _BLENDERS[0])
FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
N = {"type": "number", "optional": True}


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _p(path) -> str:
    return str(Path(os.path.expanduser(path)).resolve())


def _out(src, out, tag, ext=None) -> str:
    """Çıktı yolu: verilmediyse kaynağın yanına '_jarvis-<iş>'. Var olan dosyanın üzerine asla yazmaz."""
    s = Path(_p(src))
    o = Path(_p(out)) if out else s.with_name(f"{s.stem}_jarvis-{tag}{ext or s.suffix}")
    base, n = o, 2
    while o.exists():
        o = base.with_name(f"{base.stem}-{n}{base.suffix}")
        n += 1
    o.parent.mkdir(parents=True, exist_ok=True)
    return str(o)


def info(path) -> dict:
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", _p(path)], capture_output=True, text=True)
    e = r.stderr
    d = {}
    if (m := re.search(r"Duration: (\d+):(\d+):([\d.]+)", e)):
        d["sure"] = round(int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), 2)
    if (m := re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", e)):
        d["genislik"], d["yukseklik"] = int(m[1]), int(m[2])
    if (m := re.search(r"([\d.]+) fps", e)):
        d["fps"] = float(m[1])
    d["ses"] = "Audio:" in e
    return d


def _run(args, timeout=1800) -> str:
    r = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args],
                       capture_output=True, text=True, timeout=timeout)
    return "" if r.returncode == 0 else (r.stderr.strip()[-400:] or f"ffmpeg çıkış {r.returncode}")


def _t(v) -> float:
    """'1:23.5', '83.5', 83 → saniye."""
    if isinstance(v, (int, float)):
        return float(v)
    parts = [float(x) for x in str(v).replace(",", ".").split(":")]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


@tool("video", "Video düzenleme (ffmpeg, kare hassasiyetinde; CapCut'ta fareyle uğraşmaktan güvenilir). action: "
      "info | overlay (resmi/videoyu start-end arasında x,y konumuna koyar; x,y = görüntüde merkezin soldan/üstten oranı "
      "0-1, width = video genişliğine oran) | text (yazı ekler, aynı konum mantığı) | cut (start-end arasını TUTAR) | "
      "remove (start-end arasını SİLER) | concat (paths: virgülle videolar) | audio (müzik/ses ekler; replace=evet ise "
      "eski sesi siler) | speed (factor) | frame (start anındaki kareyi png yapar; look_image ile bak) | convert. "
      "Zaman: saniye ya da 1:23. Çıktı verilmezse kaynağın yanına yeni dosya; asıl dosyaya dokunmaz.",
      action=S("işlem"), path=S("kaynak video"), out=S("çıktı yolu", optional=True),
      media=S("overlay için resim/video, audio için ses dosyası", optional=True),
      start=S("başlangıç zamanı", optional=True), end=S("bitiş zamanı (boş = sona kadar / 3 sn)", optional=True),
      x={**N, "description": "0-1 yatay konum (merkez)"}, y={**N, "description": "0-1 dikey konum (merkez)"},
      width={**N, "description": "0-1 genişlik oranı"}, text=S("yazı", optional=True),
      size=I("yazı boyu (px)", optional=True), color=S("yazı rengi (white, red, #ffcc00)", optional=True),
      factor={**N, "description": "hız katı"}, volume={**N, "description": "ses düzeyi (1 = aynı)"},
      replace=S("evet|hayır", optional=True), paths=S("concat için virgüllü liste", optional=True))
def t_video(ctx, action, path, out="", media="", start="0", end="", x=0.5, y=0.5, width=0.3, text="", size=0,
            color="white", factor=1.0, volume=1.0, replace="hayır", paths=""):
    src = _p(path)
    if action != "concat" and not os.path.exists(src):
        return "dosya yok: " + src
    if action == "info":
        return str(info(src))
    meta = info(src) if action != "concat" else {}
    W, H, dur = meta.get("genislik", 1920), meta.get("yukseklik", 1080), meta.get("sure", 0)
    a = _t(start or 0)
    b = _t(end) if end else None
    if action == "overlay":
        m = _p(media)
        if not os.path.exists(m):
            return "eklenecek dosya yok: " + m
        b = b if b is not None else (dur if dur else a + 3)
        w = max(2, int(W * float(width)) // 2 * 2)
        px, py = float(x) * W, float(y) * H
        o = _out(src, out, "ekli")
        flt = (f"[1:v]scale={w}:-2[ov];[0:v][ov]overlay=x={px:.0f}-w/2:y={py:.0f}-h/2:shortest=1:"
               f"enable='between(t,{a:.3f},{b:.3f})'[v]")
        loop = ["-loop", "1"] if Path(m).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".heic") else []
        err = _run(["-i", src, *loop, "-i", m, "-filter_complex", flt, "-map", "[v]", "-map", "0:a?",
                    "-c:a", "copy", o])
        return err or f"hazır: {o} (resim {a:.1f}-{b:.1f} sn, merkez %{x * 100:.0f},%{y * 100:.0f})"
    if action == "text":
        b = b if b is not None else (dur if dur else a + 3)
        fs = size or max(24, H // 14)
        safe = text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")
        o = _out(src, out, "yazi")
        vf = (f"drawtext=fontfile='{FONT}':text='{safe}':fontsize={fs}:fontcolor={color}:borderw=3:"
              f"x={float(x) * W:.0f}-text_w/2:y={float(y) * H:.0f}-text_h/2:enable='between(t,{a:.3f},{b:.3f})'")
        err = _run(["-i", src, "-vf", vf, "-c:a", "copy", o])
        return err or f"hazır: {o}"
    if action == "cut":
        o = _out(src, out, "kesit")
        err = _run(["-ss", f"{a}", *(["-to", f"{b}"] if b else []), "-i", src, "-c:v", "libx264", "-c:a", "aac", o])
        return err or f"hazır: {o}"
    if action == "remove":
        if b is None:
            return "remove için end gerekli"
        o = _out(src, out, "silindi")
        keep = f"not(between(t,{a:.3f},{b:.3f}))"
        err = _run(["-i", src, "-vf", f"select='{keep}',setpts=N/FRAME_RATE/TB",
                    "-af", f"aselect='{keep}',asetpts=N/SR/TB", o])
        return err or f"hazır: {o} ({b - a:.1f} sn silindi)"
    if action == "concat":
        files = [_p(p.strip()) for p in (paths or path).split(",") if p.strip()]
        miss = [f for f in files if not os.path.exists(f)]
        if miss:
            return "yok: " + ", ".join(miss)
        o = _out(files[0], out, "birlesik")
        ins = sum((["-i", f] for f in files), [])
        n = len(files)
        w0, h0 = info(files[0]).get("genislik", 1920), info(files[0]).get("yukseklik", 1080)
        pre = "".join(f"[{i}:v]scale={w0}:{h0}:force_original_aspect_ratio=decrease,pad={w0}:{h0}:-1:-1,setsar=1[v{i}];"
                      for i in range(n))
        has_a = all(info(f).get("ses") for f in files)
        cat = "".join(f"[v{i}]" + (f"[{i}:a]" if has_a else "") for i in range(n))
        flt = pre + cat + f"concat=n={n}:v=1:a={1 if has_a else 0}[v]" + ("[a]" if has_a else "")
        err = _run([*ins, "-filter_complex", flt, "-map", "[v]", *(["-map", "[a]"] if has_a else []), o])
        return err or f"hazır: {o}"
    if action == "audio":
        m = _p(media)
        if not os.path.exists(m):
            return "ses dosyası yok: " + m
        o = _out(src, out, "sesli")
        d = int(a * 1000)
        mus = f"[1:a]adelay={d}|{d},volume={float(volume)}[m]"
        if replace.lower().startswith("e") or not meta.get("ses"):
            flt, amap = mus, "[m]"
        else:
            flt, amap = mus + ";[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]", "[a]"
        err = _run(["-i", src, "-i", m, "-filter_complex", flt, "-map", "0:v", "-map", amap, "-c:v", "copy",
                    "-shortest", o])
        return err or f"hazır: {o}"
    if action == "speed":
        f = float(factor)
        o = _out(src, out, f"hiz{f:g}")
        at = []
        r = f
        while r > 2:
            at.append("atempo=2.0")
            r /= 2
        while r < 0.5:
            at.append("atempo=0.5")
            r /= 0.5
        at.append(f"atempo={r}")
        err = _run(["-i", src, "-vf", f"setpts=PTS/{f}", *(["-af", ",".join(at)] if meta.get("ses") else []), o])
        return err or f"hazır: {o}"
    if action == "frame":
        o = _out(src, out, f"kare{a:g}", ".png")
        err = _run(["-ss", f"{a}", "-i", src, "-frames:v", "1", o])
        return err or f"kare: {o}"
    if action == "convert":
        o = _out(src, out, "donusum", Path(out).suffix if out else ".mp4")
        err = _run(["-i", src, o])
        return err or f"hazır: {o}"
    return "bilinmeyen işlem"


@tool("look_image", "Bir resim dosyasına (render, video karesi, indirilen görsel) bakıp soruyu cevaplar.",
      path=S("resim yolu"), question=S("soru"))
def t_look_image(ctx, path, question):
    p = Path(_p(path))
    if not p.exists():
        return "resim yok: " + str(p)
    tmp = Path(tempfile.mkdtemp(dir=config.path("data/tmp"))) / "bak.png"
    subprocess.run(["sips", "-s", "format", "png", "-Z", "1280", str(p), "--out", str(tmp)], capture_output=True)
    try:
        return clip(ctx.vision(question, tmp if tmp.exists() else p))
    finally:
        tmp.unlink(missing_ok=True)


BLENDER_PRE = """import bpy, bmesh, math, mathutils, os, sys
from mathutils import Vector, Euler
def jarvis_render(path, res=900):
    sc = bpy.context.scene
    objs = [o for o in sc.objects if o.type == 'MESH' and o.visible_get()]
    def flat(o):   # zemin/düzlem kadrajı büyütmesin: yüksekliği yok denecek kadar az olanlar
        d = o.dimensions
        return min(d) < 0.01 * max(max(d), 1e-6)
    objs = [o for o in objs if not flat(o)] or objs
    if not objs:
        return
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    mid, size = (lo + hi) / 2, max((hi - lo).length, 0.01)
    cam = sc.camera
    if cam is None:
        cam = bpy.data.objects.new('JarvisCam', bpy.data.cameras.new('JarvisCam'))
        sc.collection.objects.link(cam)
        sc.camera = cam
    cam.location = mid + Vector((0.9, -1.15, 0.5)) * size
    cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler()
    if not any(o.type == 'LIGHT' for o in sc.objects):
        sun = bpy.data.objects.new('JarvisSun', bpy.data.lights.new('JarvisSun', 'SUN'))
        sun.data.energy = 3
        sun.rotation_euler = (0.8, 0.2, 0.6)
        sc.collection.objects.link(sun)
    if sc.world is None:
        sc.world = bpy.data.worlds.new('W')
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get('Background')
    if bg and max(bg.inputs[0].default_value[:3]) < 0.1:      # varsayılan koyu gri dünya: aydınlık stüdyo yap
        bg.inputs[0].default_value, bg.inputs[1].default_value = (0.6, 0.65, 0.7, 1), 0.8
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in
        bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
"""


@tool("blender", "Blender'ı (HDD'de kurulu) arka planda Python (bpy) ile çalıştırır: 3B model oluşturma/düzenleme, "
      "model içe aktarma (bpy.ops.import_scene.gltf/fbx, bpy.ops.wm.obj_import), malzeme/renk, ölçü, dışa aktarma "
      "(bpy.ops.export_scene.fbx/gltf). file: açılacak .blend (boş = yeni sahne; yeni sahnede varsayılan küp/ışık/kamera "
      "var). save: kaydedilecek .blend. render: sonucu görmek için png yolu (otomatik kamera; sonra look_image). "
      "Kodda print('JARVIS:', ...) çıktısı döner. Tek seferde dev betik yazma; parça parça kur, her parçada render'a bak.",
      risk="safe", code=S("bpy Python kodu"), file=S(".blend dosyası", optional=True),
      save=S("kaydedilecek .blend yolu", optional=True), render=S("önizleme png yolu", optional=True))
def t_blender(ctx, code, file="", save="", render=""):
    if not BLENDER.exists():
        return "Blender kurulu değil (data/apps/Blender.app veya /Applications)"
    script = BLENDER_PRE + "\n" + code + "\n"
    if save:
        sp = _p(save)
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        script += f"\nbpy.ops.wm.save_as_mainfile(filepath={sp!r})\nprint('JARVIS: kaydedildi', {sp!r})\n"
    if render:
        rp = _p(render)
        os.makedirs(os.path.dirname(rp), exist_ok=True)
        script += f"\njarvis_render({rp!r})\nprint('JARVIS: render', {rp!r})\n"
    f = config.path("data/tmp/jarvis_blender.py")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(script, encoding="utf-8")
    args = [str(BLENDER), "-b", *([_p(file)] if file else []), "--python-exit-code", "1", "--python", str(f)]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        return "Blender 900 sn içinde bitmedi"
    out = r.stdout + r.stderr
    keep = [ln for ln in out.splitlines() if ln.startswith("JARVIS") or re.search(r"Error|Traceback|line \d+", ln)]
    return clip(f"[çıkış {r.returncode}]\n" + ("\n".join(keep[-40:]) or out[-1200:]), 3000)
