from app import process_input

test_inputs = [
    "Track Apple stock",
    "Buy Tesla stock",
    "Watch XYZ and buy when good",
    "Sell Reliance when price drops below 2000"
]

for text in test_inputs:
    print("\nINPUT:", text)
    result = process_input(text)
    print("OUTPUT:", result["final"])