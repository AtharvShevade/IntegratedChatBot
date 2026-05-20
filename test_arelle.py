from arelle import Cntlr
from arelle import ModelManager

INSTANCE_PATH = r"C:\Users\atharv.shevade\Desktop\Chat-System\logs\HDFC240615R00902D_08-01-25_01-19-20_Instance.xml"

# Create controller
cntlr = Cntlr.Cntlr()

# Initialize model manager
model_manager = ModelManager.initialize(cntlr)

# Disable strict validation
model_manager.validateDisclosureSystem = False
model_manager.validateInferDecimals = False

print("Loading XBRL...")

# Load XBRL instance
model_xbrl = model_manager.load(INSTANCE_PATH)

print("\nLoaded Successfully!\n")

print("Facts found:", len(model_xbrl.facts))

print("\n===== FACTS =====\n")

for fact in model_xbrl.facts:
    try:
        print(
            f"Concept: {fact.qname.localName} | "
            f"Value: {fact.value} | "
            f"Context: {fact.contextID}"
        )
    except Exception as e:
        print("Error reading fact:", e)

print("\nDone.")
