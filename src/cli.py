import numpy as np
from database import Database

def main():

    print("\nWelcome to Noted.\n")

    db = Database()
    db.create_notes_table()

    while True:

        user_choice = input("Choose an option:\n1. Enter a note\n2. List all notes\n3. List a specific note\n4. Edit a note\n5. Delete a note\nYour choice: ")

        if user_choice == '1':
            print("Enter the data for your note or leave it blank.")
            title = input("Choose a title for your note: ")
            contents = input("Enter the contents of your note: ")
            tags = input("Enter comma separated tags for your note: ")
            embeddings = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()
            note_id = db.create_note(title, contents, embeddings, tags)
            print(f"You succesfully entered a note with an ID of {note_id}")

        elif user_choice == '2':
            deleted = input("Would you like to see deleted notes as well? Yes/No: ")
            result = None
            if deleted == "Yes":
                result = db.list_all_notes(include_deleted=True)
            elif deleted == "No":
                result = db.list_all_notes()
            else:
                print("Invalid choice. Try again.")
                continue
            for res in result:
                print(res)

        elif user_choice == '3':
            note_id = input("Enter ID of note to view (an integer): ")
            note_id = int(note_id)
            note = db.get_note(note_id)
            print(note)

        elif user_choice == '4':
            note_id = input("Enter ID of note to edit (an integer): ")
            title = input("Enter a new title (or leave blank to remain unchanged): ")
            contents = input("Enter the new contetns (or leave blank): ")
            tags = input("Enter the new tags (or leave blank): ")
            title = title if title.strip() != "" else None
            contents = contents if contents.strip() != "" else None
            tags = tags if tags.strip() != "" else None

            db.update_note(int(note_id), title, contents, tags)

            print("Note updated.")
            
        elif user_choice == '5':
            note_id = input("Enter ID of note to delete (an integer): ")
            db.mark_note_as_deleted(note_id)
            print(f"Note {note_id} marked as deleted.")
        else:
            print("\nInvalid choice. Try again or press ctrl c to exit.\n")

if __name__ == "__main__":

    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit
