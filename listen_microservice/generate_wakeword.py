import os

instructions = """
======================================================================
                 WAKE WORD GENERATION INSTRUCTIONS
======================================================================

OpenWakeWord provides an automated way to train custom models (like "Dhatri") 
by synthesizing thousands of examples using Text-to-Speech models. 

Because training a robust model requires downloading ~1-2 GBs of base datasets 
and running heavy TTS generation, it is highly recommended to run the training 
in the cloud (Google Colab) and just download the resulting `dhatri.tflite` model.

Once the model is generated, the `listen_microservice` itself runs 100% OFFLINE.

### Step 1: Open the Official OpenWakeWord Colab Notebook
Navigate to:
https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb

### Step 2: Configure the Training
In the notebook, set:
- target_word = "dhatri"

### Step 3: Run the Notebook
Execute the cells in the notebook. It will take about 10-15 minutes to train.

### Step 4: Download and place the model
The notebook will generate a file named `dhatri.tflite`.
Download it and place it in the following directory on this PC:
"""

print(instructions)
print(os.path.abspath(os.path.join(os.path.dirname(__file__), 'models', 'dhatri.tflite')))
print("\n======================================================================")
