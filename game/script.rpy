## The script of the game goes in this file.
#
## Declare characters used by this game. The color argument colorizes the name
## of the character.

define e = Character('Eileen')

## The game starts here.


label cancel:

    "With 'Cancel' you discard changes. That's just fleeing from syntax errors; also unapplied benign changes are lost."

    "'Visual' in the editor returns you to visual modus. changes are kept in memory, but lost after a reload or something similar. to store them it is safest to apply changes."

    "Applied changes are written to the .rpy file on disk. Make sure that you're not working on this .rpy file in another editor. It's advisable to have backups or work with version control."

    "Now return to the editor modus."

    # Let's replace the text in the narration below here:

    "Replace this text."

    # You can use the mouse or shift arrow movement for selection and some common keyboard shortcuts are available.

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

    # Now you've entered the edit modus. In here you can make edit your Ren'py script. With the visual
    # button, below, you can return to where you were in the visual novel, but let's stay in editor
    # modus for a bit.

    # Move the cursor by mouse click or keyboard arrows. Then, for instance, try adding dots to this line..

    # You may have noticed that now 3 buttons are shown at the bottom: Apply, Cancel and Visual.

    # However, if you add something that is not valid ren'py..

    # ..you see a warning and 'Hide' is shown (or 'Debug' if the error is hidden), instead of Apply.

    # Now press Cancel, and continue the visual novel to the next line..

    jump cancel











label applied:

    "When you returned from the visual modus, you may have observed the reload. That is required so your applied change is shown in visual modus. A reload can also be triggered with shift+r."

    "Sometimes a change can cause the visual novel to restart. During development you can add jumps to fast forward dialogue."

    "The editor has some more quirks, and lacks features, but should already be a bit useful. let's go back to the editor once more."

    # something goes wrong when scrolling near long lines

    # All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. All work and no play makes Jack a dull boy. 
    "End of file."

    return
