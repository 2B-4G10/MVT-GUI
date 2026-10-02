import sys
import traceback


def report(error: BaseException) -> None:
    """The app has no console, so a failure to start would otherwise go
    unnoticed. Saves the details and shows them in a message box."""
    details = "".join(traceback.format_exception(error))
    try:
        from mvtwin import environment

        log = environment.data_folder() / "error.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(details, encoding="utf-8")
        where = f"\n\nThe details are saved in {log}."
    except Exception:
        where = ""
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            f"MVT for Windows couldn't start:\n\n{error}{where}",
            "MVT for Windows",
            0x10,
        )
    else:
        print(details, file=sys.stderr)


try:
    from mvtwin.app import main

    code = main()
except Exception as error:
    report(error)
    code = 1
sys.exit(code)
