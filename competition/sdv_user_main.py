from competition import sdv_config as cfg

USER_MAIN_KIND = "python"


async def main(zbot):
    program = str(cfg.PROGRAM).lower()

    if program == "solo":
        from competition.format_a_solo_loop import main as run
    elif program == "alliance":
        from competition.format_b_alliance_shuttle import main as run
    elif program == "sensor_check":
        from competition.sdv_sensor_check import main as run
    else:
        raise ValueError("unknown SDV program: {}".format(cfg.PROGRAM))

    zbot.display("SDV", program)
    await run(zbot)
