## The script of the game goes in this file.

## Declare characters used by this game. The color argument colorizes the name
## of the character.

define e = Character('Eileen')

## The game starts here.


label cancel:

    "With 'Cancel' you discard changes. That's one way to get rid of a syntax error."

    "'Visual' in the editor returns you to the visual modus, any changes are in that case only kept in store."

    "If you want to write changes, 'Apply' writes the edits to the .rpy file on disk. Make sure that you're not working on this .rpy file in an external editor as well."

    "Now return to the editor modus. When you've returned from the visual modus, press shift+R to see the change you made in the next dialogue."

    # Now let's replace the text in the narration below here:

    "Replace this text."

    # You can use the mouse for selection and some common keyboard shortcuts are available.

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

    "This visual novel has a built-in editor. Note the buttons below. Press the Edit button to continue."

    # Now you've entered the edit modus. In here you can make changes to your Ren'py script.
    # You can move the cursor by mouse or keyboard arrows.

    # For instance, try adding dots to this line..

    # ..and you may notice that now 3 buttons are shown at the bottom of the editor:

    # Apply, Cancel and Visual.

    # But, if you add something random on the non-comment line below here..

    # ..you will see a debug warning and 'Silence' or 'Debug' instead of the Apply button.

    # Now press Cancel, and continue the visual novel to the next line..

    jump cancel











label applied:

    "It may happen that reload is triggered automaticly, and it can also cause the visual novel to restart."

    "The editor has some more quirks, and probably lacks some features, but is IMhO already somewhat useful."

    "End of file."

    return
