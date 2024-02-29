import pandas as pd

# Read the CSV file into a DataFrame
df = pd.read_csv('gutenberg_metadata.csv')

# Function to generate readlink from the given Link
def generate_readlink(link):
    book_number = link.split('/')[-1]  # Extract the book number
    return link.replace('/ebooks/', f'/cache/epub/{book_number}/pg').replace('http:', 'https:') + '-images.html'

# Function to generate imglink from the given Link
def generate_imglink(link):
    book_number = link.split('/')[-1]  # Extract the book number
    return link.replace('/ebooks/', f'/cache/epub/{book_number}/pg').replace('http:', 'https:') + '.cover.medium.jpg'

# Add readlink and imglink columns to the DataFrame
df['readlink'] = df['Link'].apply(generate_readlink)
df['imglink'] = df['Link'].apply(generate_imglink)

# Save the modified DataFrame back to a CSV file
df.to_csv('modified_file.csv', index=False)
