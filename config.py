import os

ROOT_DATA_DIR = "data"

DATASETS = [
    {
        "name": "DynAction4D",
        "path": os.path.join(ROOT_DATA_DIR, "Sample_DynAction4D"),
        "color": "#2b6cb0",
        "overide_color": False,
        "actor_label_prefixes": ("male_", "female_"),
    },
    {
        "name": "DynAction4D 2",
        "path": os.path.join(ROOT_DATA_DIR, "Sample_DynAction4D_2"),
        "color": "#c05621",
        "overide_color": True,
        "actor_label_prefixes": ("male_", "female_"),
    },
    {
        "name": "DynAction4D 3",
        "path": os.path.join(ROOT_DATA_DIR, "Sample_DynAction4D_3"),
        "color": "#2f855a",
        "overide_color": True,
        "actor_label_prefixes": ("male_", "female_"),
    },
]
