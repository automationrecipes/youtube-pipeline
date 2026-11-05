"""Daily run: idea -> script -> voice -> video -> thumbnail -> upload -> log."""
import datetime as dt
import json
import shutil
from . import config as C
from .script_writer import write_package, save_history
from .render import render
from .thumbnail import make as make_thumb


def main():
    stamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M")
    work = C.OUT / stamp
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    print("1/4 writing script")
    pkg = write_package()
    (work / "package.json").write_text(json.dumps(pkg, indent=2))
    print(f"  title: {pkg['title']}")

    print("2/4 rendering video")
    video = render(pkg, work)

    print("3/4 thumbnail")
    thumb = None if C.IS_SHORT else make_thumb(video, pkg.get("thumbnail_text", pkg["title"]),
                                               work / "thumbnail.jpg")

    video_id = None
    if C.DRY_RUN:
        print("4/4 DRY_RUN=1, skipping upload")
    else:
        print("4/4 uploading")
        from .upload import upload
        video_id = upload(pkg, video, thumb)

    save_history({"date": stamp, "title": pkg["title"], "format": C.VIDEO_FORMAT,
                  "video_id": video_id})
    print("done")


if __name__ == "__main__":
    main()
