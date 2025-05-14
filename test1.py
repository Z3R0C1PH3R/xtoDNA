nucleotides = ["A", "C", "G", "T"]
inverse_nucleotides = {n: f"{i:02b}" for i, n in enumerate(nucleotides)}
print(inverse_nucleotides)

with open("input.txt", "r+b") as f:
    data = f.read()

print(data)

nucleotides_list = []
for i in data:
    binary = f"{i:08b}"
    nucleotides_list.extend([nucleotides[int(binary[j:j+2], 2)] for j in range(0, 8, 2)])

print("".join(nucleotides_list))

string = ""
for i in nucleotides_list:
    string += inverse_nucleotides[i]

print(string)

byte_array = bytearray(int(string[i:i + 8], 2) for i in range(0, len(string), 8))
print(byte_array)