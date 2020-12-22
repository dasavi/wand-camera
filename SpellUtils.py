
from GoogleAssistantUtils import playMusic, command, broadcast

def PerformSpell(spell):
    """
    Make the desired Home Assistant REST API call based on the spell
    """
    if(spell == "circle"):
        circleSpell()
    elif(spell == "incendio"):
        incendioSpell()
        
    print("ACTIVATE SPELL: " + spell)

def circleSpell():
    command("turn off guest room lights")
    command("turn on galaxy")
    playMusic()

def incendioSpell():
    command("turn off galaxy")
    command("stop playing music")
    command("turn on the guest room lights")