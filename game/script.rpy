## The script of the game goes in this file.
#
## Declare characters used by this game. The color argument colorizes the name
## of the character.

define e = Character('Eileen')

## The game starts here.


label cancel:

    "With 'Cancel' you discard changes. That's just fleeing from syntax errors; also unapplied benign changes are lost."

    "'Visual' in the editor returns you to visual modus. changes are kept in memory, but lost after a reload or something similar. to store them it is safest to apply changes."

    "Applied changes are written to the .rpy file on disk. Make sure that you're not working on this same .rpy file in an external editor, and keep some backups. Now return to the editor modus."

    # Let's replace the text in the narration below here:

    "Make changes to this text."

    # For selection, you can use the mouse drag or doubleclick on words and use shift (+ ctrl) and keyboard arrow movement ctrl+x and some common keyboard shortcuts are available.

    # changes can be undone with Ctrl+u and redone with Ctrl+z although undoing many changes is a bit quirky still

    # Apply the change (write the change to disk) and you will return to visual modus.

    jump applied

label start:

    ## Show a background. This uses a placeholder by default, but you can add a
    ## file (named either "bg room.png" or "bg room.jpg") to the images
    ## directory to show it.

    scene bg room

    ## This shows a character sprite. A placeholder is used, but you can replace
    ## it by adding a file named "eileen happy.png" to the images directory.

    show eileen happy

    ## These display lines of dialogue.

    "This visual novel has a built-in editor. Note the Edit button below. Press it to try it out."

    # Now you've entered the edit modus where you change your Ren'py script. With the visual
    # button, below, you return to where you left off in the visual novel.

    # Keyboard and mouse are functional. If you add for instance dots to this line..

    # You may notice now 3 buttons are shown in the quickmenu below: Apply, Cancel and Visual.

    # If you add something that is not valid ren'py, however you'll get a warning and the apply button is replaced by Hide (or 'Debug' when pressed).

    # Now press Cancel, and continue the visual novel to the next line..

    jump cancel











label applied:

    "When you returned from the visual modus, you may have observed a reload. Reload is required to see applied changes in visual modus. A reload can also be triggered with shift+r (but unapplied changes are lost!)."

    "Sometimes a change can cause the visual novel to restart. A bit annoying but maybe just add some jumps to fast forward dialogue."

    "The editor has more quirks, and lacks features, but should already be a bit useful. let's go back to the editor once more."

    # There is a find function, which you can trigger with ctrl+f, but sometimes the highlighted string is off-by one. Regex replacement is what I'd like to add when it's fixed.

    # scrolling near long lines is a bit odd:

    # All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy.

    # maybe insertion of code templates could be nice.


    "End of file."

    return
