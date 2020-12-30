ASSISTANT_USER="Avi"
ASSISTANT_RELAY_HOST="http://ar.local:3000"
ASSISTANT_URL=ASSISTANT_RELAY_HOST + "/assistant"
CAST_URL=ASSISTANT_RELAY_HOST + "/cast/"
CAST_DEVICE="Study speaker"
MUSIC_URL="https://www.youtube.com/watch?v=u-TuSh68y08"
TRAINING_IMAGE_SIZE_X=50
TRAINING_IMAGE_SIZE_Y=50
CAPTURE_MODE=True
CAPTURE_FOLDER="./images/captured"
CLASS_MAPPING = {
    0: "mistakes",
    1: "aguamenti",
    2: "tarantallegra",
    3: "circle",
    4: "squares",
    5: "incendio"
}