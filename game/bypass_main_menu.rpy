
# bypass main menu and quit confirmation
label main_menu:
    $ config.quit_action = Quit(confirm=False)
    return

