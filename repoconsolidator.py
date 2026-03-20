import os

# Output file
output_file = "consolidated_repo.txt"

with open(output_file, "w", encoding="utf-8") as outfile:
    for root, dirs, files in os.walk("."):  # Current directory as root
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                # Write a header for each file
                outfile.write(f"\n\n--- File: {file_path} ---\n\n")
                outfile.write(content)
            except Exception as e:
                print(f"Skipping {file_path} due to error: {e}")

print(f"Consolidation complete! Output saved to {output_file}")
