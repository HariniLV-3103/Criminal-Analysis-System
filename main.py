import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog
from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId
from datetime import datetime
from PIL import Image, ImageTk
import os

client = MongoClient("mongodb://localhost:27017/")
db = client["crime_analysis"]
fs = gridfs.GridFS(db)
criminals = db["criminals"]
cases = db["cases"]

root = tk.Tk()
root.title("Crime Analysis System")
root.geometry("600x400")

def add_criminal():
    def submit():
        criminal_id = id_entry.get()
        # Check if criminal ID already exists
        if criminals.find_one({"custom_id": criminal_id}):
            messagebox.showerror("Error", "Criminal ID must be unique.")
            return
        
        data = {
            "custom_id": criminal_id,
            "name": name_entry.get(),
            "age": age_entry.get(),
            "gender": gender_entry.get(),
            "crime": crime_entry.get(),
            "status": status_entry.get()
        }
        criminals.insert_one(data)
        messagebox.showinfo("Success", "Criminal added successfully")
        window.destroy()

    window = tk.Toplevel(root)
    window.title("Add Criminal")
    
    # Create form fields
    tk.Label(window, text="Criminal ID*").grid(row=0, column=0)
    tk.Label(window, text="Name*").grid(row=1, column=0)
    tk.Label(window, text="Age").grid(row=2, column=0)
    tk.Label(window, text="Gender").grid(row=3, column=0)
    tk.Label(window, text="Crime").grid(row=4, column=0)
    tk.Label(window, text="Status").grid(row=5, column=0)

    id_entry = tk.Entry(window)
    name_entry = tk.Entry(window)
    age_entry = tk.Entry(window)
    gender_entry = ttk.Combobox(window, values=["Male", "Female", "Other"])
    crime_entry = tk.Entry(window)
    status_entry = ttk.Combobox(window, values=["Active", "Inactive", "Incarcerated", "Deceased"])

    id_entry.grid(row=0, column=1)
    name_entry.grid(row=1, column=1)
    age_entry.grid(row=2, column=1)
    gender_entry.grid(row=3, column=1)
    crime_entry.grid(row=4, column=1)
    status_entry.grid(row=5, column=1)

    tk.Button(window, text="Submit", command=submit).grid(row=6, columnspan=2)

def add_biometric():
    selected_files = []

    def browse_images():
        files = filedialog.askopenfilenames(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if files:
            selected_files.clear()
            selected_files.extend(files)
            entry_path.delete(0, tk.END)
            entry_path.insert(0, "; ".join(os.path.basename(f) for f in selected_files))

    def submit():
        criminal_id = entry_criminal_id.get().strip()
        bio_type = entry_type.get()

        if not all([criminal_id, bio_type, selected_files]):
            messagebox.showwarning("Warning", "Please fill in all fields and select images.")
            return

        # Check if criminal exists (using custom_id field)
        criminal = criminals.find_one({"custom_id": criminal_id})
        if not criminal:
            messagebox.showerror("Error", f"No criminal found with ID '{criminal_id}'")
            return

        # Create biometric_data collection if it doesn't exist
        if "biometric_data" not in db.list_collection_names():
            db.create_collection("biometric_data")

        # Upload each image
        for image_path in selected_files:
            try:
                with open(image_path, "rb") as f:
                    file_id = fs.put(f, filename=os.path.basename(image_path), criminal_id=criminal_id)
                    db["biometric_data"].insert_one({
                        "criminal_id": criminal_id,
                        "type": bio_type,
                        "file_id": file_id,
                        "timestamp": datetime.now()
                    })
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload {os.path.basename(image_path)}: {str(e)}")
                return

        messagebox.showinfo("Success", "Biometric data added successfully")
        add_window.destroy()

    add_window = tk.Toplevel(root)
    add_window.title("Add Biometric Data")

    tk.Label(add_window, text="Criminal ID*:").grid(row=0, column=0)
    tk.Label(add_window, text="Biometric Type*:").grid(row=1, column=0)
    tk.Label(add_window, text="Images*:").grid(row=2, column=0)

    entry_criminal_id = tk.Entry(add_window)
    entry_type = ttk.Combobox(add_window, values=["Fingerprint", "Face", "DNA", "Other"])
    entry_path = tk.Entry(add_window, width=40)

    entry_criminal_id.grid(row=0, column=1)
    entry_type.grid(row=1, column=1)
    entry_path.grid(row=2, column=1)
    tk.Button(add_window, text="Browse", command=browse_images).grid(row=2, column=2)

    tk.Button(add_window, text="Submit", command=submit).grid(row=3, columnspan=3, pady=10)

def view_criminals():
    view_window = tk.Toplevel(root)
    view_window.title("View Criminals")
    view_window.geometry("800x600")
    
    # Create a canvas and scrollbar for scrollable content
    canvas = tk.Canvas(view_window)
    scrollbar = ttk.Scrollbar(view_window, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    row = 0
    for criminal in criminals.find():
        # Create a frame for each criminal
        criminal_frame = ttk.LabelFrame(scrollable_frame, text=f"Criminal: {criminal.get('name', 'N/A')}")
        criminal_frame.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        
        # Criminal information
        info_text = (
            f"ID: {criminal.get('custom_id', 'N/A')}\n"
            f"Age: {criminal.get('age', 'N/A')}\n"
            f"Gender: {criminal.get('gender', 'N/A')}\n"
            f"Crime: {criminal.get('crime', 'N/A')}\n"
            f"Status: {criminal.get('status', 'N/A')}"
        )
        
        info_label = ttk.Label(criminal_frame, text=info_text)
        info_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Get biometric images for this criminal
        bio_images = []
        if "biometric_data" in db.list_collection_names():
            bios = db["biometric_data"].find({"criminal_id": criminal.get("custom_id")})
            
            col = 1  # Start column for images
            for bio in bios:
                try:
                    file_id = bio.get("file_id")
                    if file_id:
                        img_data = fs.get(file_id).read()
                        
                        # Create temporary file
                        temp_filename = f"temp_img_{file_id}.jpg"
                        with open(temp_filename, "wb") as f:
                            f.write(img_data)
                            
                        # Open and resize image
                        image = Image.open(temp_filename)
                        image.thumbnail((150, 150))
                        photo = ImageTk.PhotoImage(image)
                        bio_images.append(photo)  # Keep reference
                        
                        # Create image label
                        img_frame = ttk.Frame(criminal_frame)
                        img_frame.grid(row=0, column=col, padx=5, pady=5)
                        
                        img_label = ttk.Label(img_frame, image=photo)
                        img_label.image = photo  # Keep reference
                        img_label.pack()
                        
                        # Add image info
                        ttk.Label(img_frame, 
                                  text=f"Type: {bio.get('type', 'N/A')}",
                                  font=('Arial', 8)).pack()
                        
                        col += 1
                except Exception as e:
                    print(f"Error loading image: {e}")
                    continue
        
        row += 1
    
    # Add a button to refresh the view
    refresh_btn = ttk.Button(scrollable_frame, text="Refresh", 
                            command=lambda: [view_window.destroy(), view_criminals()])
    refresh_btn.grid(row=row, column=0, pady=10)


def update_criminal():
    custom_id = simpledialog.askstring("Input", "Enter Custom ID of criminal to update")
    crim = criminals.find_one({"custom_id": custom_id})
    if not crim:
        messagebox.showerror("Error", "Criminal not found")
        return

    def submit():
        criminals.update_one({"custom_id": custom_id}, {"$set": {
            "age": age_entry.get(),
            "gender": gender_entry.get(),
            "crime": crime_entry.get(),
            "status": status_entry.get()
        }})
        messagebox.showinfo("Success", "Criminal updated successfully")
        window.destroy()

    window = tk.Toplevel(root)
    window.title("Update Criminal")
    tk.Label(window, text="Age").grid(row=0, column=0)
    tk.Label(window, text="Gender").grid(row=1, column=0)
    tk.Label(window, text="Crime").grid(row=2, column=0)
    tk.Label(window, text="Status").grid(row=3, column=0)

    age_entry = tk.Entry(window)
    gender_entry = tk.Entry(window)
    crime_entry = tk.Entry(window)
    status_entry = tk.Entry(window)

    age_entry.insert(0, crim["age"])
    gender_entry.insert(0, crim["gender"])
    crime_entry.insert(0, crim["crime"])
    status_entry.insert(0, crim["status"])

    age_entry.grid(row=0, column=1)
    gender_entry.grid(row=1, column=1)
    crime_entry.grid(row=2, column=1)
    status_entry.grid(row=3, column=1)

    tk.Button(window, text="Submit", command=submit).grid(row=4, columnspan=2)



def delete_criminal():
    custom_id = simpledialog.askstring("Input", "Enter Custom ID of criminal to delete")
    result = criminals.delete_one({"custom_id": custom_id})
    if result.deleted_count:
        messagebox.showinfo("Success", "Criminal deleted successfully")
    else:
        messagebox.showerror("Error", "Criminal not found")

def search_criminal():
    name = simpledialog.askstring("Input", "Enter name to search")
    crim = criminals.find_one({"name": name})
    if crim:
        info = f"Name: {crim['name']}\nAge: {crim['age']}\nGender: {crim['gender']}\nCrime: {crim['crime']}\nStatus: {crim['status']}"
        messagebox.showinfo("Result", info)
    else:
        messagebox.showerror("Error", "Criminal not found")

def criminal_menu():
    window = tk.Toplevel(root)
    window.title("Criminal Management")
    options = [
        ("Add Criminal", add_criminal),
        ("View Criminals", view_criminals),
        ("Update Criminal", update_criminal),
        ("Delete Criminal", delete_criminal),
        ("Search Criminal", search_criminal),
        ("Add Biometric", add_biometric)
    ]
    for text, cmd in options:
        tk.Button(window, text=text, width=30, command=cmd).pack(pady=5)

def add_case():
    def submit():
        data = {
            "case_id": case_id_entry.get(),
            "description": description_entry.get(),
            "status": status_entry.get(),
            "officer": officer_entry.get()
        }
        cases.insert_one(data)
        messagebox.showinfo("Success", "Case added successfully")
        window.destroy()

    window = tk.Toplevel(root)
    window.title("Add Case")
    tk.Label(window, text="Case ID").grid(row=0, column=0)
    tk.Label(window, text="Description").grid(row=1, column=0)
    tk.Label(window, text="Status").grid(row=2, column=0)
    tk.Label(window, text="Officer Assigned").grid(row=3, column=0)

    case_id_entry = tk.Entry(window)
    description_entry = tk.Entry(window)
    status_entry = tk.Entry(window)
    officer_entry = tk.Entry(window)

    case_id_entry.grid(row=0, column=1)
    description_entry.grid(row=1, column=1)
    status_entry.grid(row=2, column=1)
    officer_entry.grid(row=3, column=1)

    tk.Button(window, text="Submit", command=submit).grid(row=4, columnspan=2)

def view_cases():
    window = tk.Toplevel(root)
    window.title("View Cases")
    tree = ttk.Treeview(window, columns=("case_id", "description", "status", "officer"), show="headings")
    for col in tree["columns"]:
        tree.heading(col, text=col)
    for case in cases.find():
        tree.insert("", "end", values=(case["case_id"], case["description"], case["status"], case["officer"]))
    tree.pack(fill="both", expand=True)

def case_menu():
    window = tk.Toplevel(root)
    window.title("Case Management")
    options = [
        ("Add Case", add_case),
        ("View Cases", view_cases)
    ]
    for text, cmd in options:
        tk.Button(window, text=text, width=30, command=cmd).pack(pady=5)

def add_victim_witness():
    def submit():
        data = {
            "name": name_entry.get(),
            "age": age_entry.get(),
            "gender": gender_entry.get(),
            "crime": crime_entry.get(),
            "role": role_entry.get(),  # Victim or Witness
            "statement": statement_entry.get()
        }
        db["victims_witnesses"].insert_one(data)
        messagebox.showinfo("Success", "Victim/Witness added successfully")
        window.destroy()

    window = tk.Toplevel(root)
    window.title("Add Victim/Witness")
    tk.Label(window, text="Name").grid(row=0, column=0)
    tk.Label(window, text="Age").grid(row=1, column=0)
    tk.Label(window, text="Gender").grid(row=2, column=0)
    tk.Label(window, text="Crime").grid(row=3, column=0)
    tk.Label(window, text="Role (Victim/Witness)").grid(row=4, column=0)
    tk.Label(window, text="Statement").grid(row=5, column=0)

    name_entry = tk.Entry(window)
    age_entry = tk.Entry(window)
    gender_entry = tk.Entry(window)
    crime_entry = tk.Entry(window)
    role_entry = tk.Entry(window)
    statement_entry = tk.Entry(window)

    name_entry.grid(row=0, column=1)
    age_entry.grid(row=1, column=1)
    gender_entry.grid(row=2, column=1)
    crime_entry.grid(row=3, column=1)
    role_entry.grid(row=4, column=1)
    statement_entry.grid(row=5, column=1)

    tk.Button(window, text="Submit", command=submit).grid(row=6, columnspan=2)

def view_victims_witnesses():
    window = tk.Toplevel(root)
    window.title("View Victims/Witnesses")
    tree = ttk.Treeview(window, columns=("name", "age", "gender", "crime", "role", "statement"), show="headings")
    for col in tree["columns"]:
        tree.heading(col, text=col)
    for vic_wit in db["victims_witnesses"].find():
        tree.insert("", "end", values=(vic_wit["name"], vic_wit["age"], vic_wit["gender"], vic_wit["crime"], vic_wit["role"], vic_wit["statement"]))
    tree.pack(fill="both", expand=True)

def update_victim_witness():
    name = simpledialog.askstring("Input", "Enter name of victim/witness to update")
    vic_wit = db["victims_witnesses"].find_one({"name": name})
    if not vic_wit:
        messagebox.showerror("Error", "Victim/Witness not found")
        return

    def submit():
        db["victims_witnesses"].update_one({"name": name}, {"$set": {
            "age": age_entry.get(),
            "gender": gender_entry.get(),
            "crime": crime_entry.get(),
            "role": role_entry.get(),
            "statement": statement_entry.get()
        }})
        messagebox.showinfo("Success", "Victim/Witness updated successfully")
        window.destroy()

    window = tk.Toplevel(root)
    window.title("Update Victim/Witness")
    tk.Label(window, text="Age").grid(row=0, column=0)
    tk.Label(window, text="Gender").grid(row=1, column=0)
    tk.Label(window, text="Crime").grid(row=2, column=0)
    tk.Label(window, text="Role (Victim/Witness)").grid(row=3, column=0)
    tk.Label(window, text="Statement").grid(row=4, column=0)

    age_entry = tk.Entry(window)
    gender_entry = tk.Entry(window)
    crime_entry = tk.Entry(window)
    role_entry = tk.Entry(window)
    statement_entry = tk.Entry(window)

    age_entry.insert(0, vic_wit["age"])
    gender_entry.insert(0, vic_wit["gender"])
    crime_entry.insert(0, vic_wit["crime"])
    role_entry.insert(0, vic_wit["role"])
    statement_entry.insert(0, vic_wit["statement"])

    age_entry.grid(row=0, column=1)
    gender_entry.grid(row=1, column=1)
    crime_entry.grid(row=2, column=1)
    role_entry.grid(row=3, column=1)
    statement_entry.grid(row=4, column=1)

    tk.Button(window, text="Submit", command=submit).grid(row=5, columnspan=2)

def delete_victim_witness():
    name = simpledialog.askstring("Input", "Enter name of victim/witness to delete")
    result = db["victims_witnesses"].delete_one({"name": name})
    if result.deleted_count:
        messagebox.showinfo("Success", "Victim/Witness deleted")
    else:
        messagebox.showerror("Error", "Victim/Witness not found")

def search_victim_witness():
    name = simpledialog.askstring("Input", "Enter name to search")
    vic_wit = db["victims_witnesses"].find_one({"name": name})
    if vic_wit:
        info = f"Name: {vic_wit['name']}\nAge: {vic_wit['age']}\nGender: {vic_wit['gender']}\nCrime: {vic_wit['crime']}\nRole: {vic_wit['role']}\nStatement: {vic_wit['statement']}"
        messagebox.showinfo("Result", info)
    else:
        messagebox.showerror("Error", "Victim/Witness not found")

def victim_witness_menu():
    window = tk.Toplevel(root)
    window.title("Victim & Witness Management")
    options = [
        ("Add Victim/Witness", add_victim_witness),
        ("View Victims/Witnesses", view_victims_witnesses),
        ("Update Victim/Witness", update_victim_witness),
        ("Delete Victim/Witness", delete_victim_witness),
        ("Search Victim/Witness", search_victim_witness)
    ]
    for text, cmd in options:
        tk.Button(window, text=text, width=30, command=cmd).pack(pady=5)

fs = gridfs.GridFS(db)

# Function to add evidence
def add_evidence():
    def submit():
        # Collect form data
        evidence_type = type_entry.get()
        description = description_entry.get()
        case_id = case_id_entry.get()
        
        # Handle file upload
        evidence_file = file_entry.get()  # This is just the filename or file path
        file_data = None
        if evidence_file:
            with open(evidence_file, 'rb') as f:
                file_data = fs.put(f, filename=evidence_file)

        # Create evidence document
        evidence_data = {
            "type": evidence_type,
            "description": description,
            "case_id": case_id,
            "file_id": file_data,  # Store file reference
        }
        db["evidence"].insert_one(evidence_data)
        messagebox.showinfo("Success", "Evidence added successfully")
        window.destroy()

    window = tk.Toplevel(root)
    window.title("Add Evidence")
    
    # Create form fields
    tk.Label(window, text="Evidence Type").grid(row=0, column=0)
    tk.Label(window, text="Description").grid(row=1, column=0)
    tk.Label(window, text="Case ID").grid(row=2, column=0)
    tk.Label(window, text="File (optional)").grid(row=3, column=0)

    type_entry = tk.Entry(window)
    description_entry = tk.Entry(window)
    case_id_entry = tk.Entry(window)
    file_entry = tk.Entry(window)  # For file input (path)

    type_entry.grid(row=0, column=1)
    description_entry.grid(row=1, column=1)
    case_id_entry.grid(row=2, column=1)
    file_entry.grid(row=3, column=1)

    tk.Button(window, text="Submit", command=submit).grid(row=4, columnspan=2)

# Function to view evidence
def view_evidence():
    window = tk.Toplevel(root)
    window.title("View Evidence")
    
    tree = ttk.Treeview(window, columns=("type", "description", "case_id"), show="headings")
    for col in tree["columns"]:
        tree.heading(col, text=col)
    
    for evidence in db["evidence"].find():
        # Retrieve file name for display (if present)
        file_name = "None"
        if evidence["file_id"]:
            file_data = fs.get(evidence["file_id"])
            file_name = file_data.filename
        
        tree.insert("", "end", values=(evidence["type"], evidence["description"], evidence["case_id"], file_name))
    
    tree.pack(fill="both", expand=True)

# Function to update evidence
def update_evidence():
    evidence_id = simpledialog.askstring("Input", "Enter Evidence ID to update")
    evidence = db["evidence"].find_one({"_id": ObjectId(evidence_id)})
    
    if not evidence:
        messagebox.showerror("Error", "Evidence not found")
        return

    def submit():
        updated_data = {
            "type": type_entry.get(),
            "description": description_entry.get(),
            "case_id": case_id_entry.get(),
        }

        # Handle file update (if provided)
        new_file = file_entry.get()
        if new_file:
            with open(new_file, 'rb') as f:
                file_data = fs.put(f, filename=new_file)
            updated_data["file_id"] = file_data

        db["evidence"].update_one({"_id": ObjectId(evidence_id)}, {"$set": updated_data})
        messagebox.showinfo("Success", "Evidence updated successfully")
        window.destroy()

    window = tk.Toplevel(root)
    window.title("Update Evidence")
    
    tk.Label(window, text="Evidence Type").grid(row=0, column=0)
    tk.Label(window, text="Description").grid(row=1, column=0)
    tk.Label(window, text="Case ID").grid(row=2, column=0)
    tk.Label(window, text="File (optional)").grid(row=3, column=0)

    type_entry = tk.Entry(window)
    description_entry = tk.Entry(window)
    case_id_entry = tk.Entry(window)
    file_entry = tk.Entry(window)

    type_entry.insert(0, evidence["type"])
    description_entry.insert(0, evidence["description"])
    case_id_entry.insert(0, evidence["case_id"])

    type_entry.grid(row=0, column=1)
    description_entry.grid(row=1, column=1)
    case_id_entry.grid(row=2, column=1)
    file_entry.grid(row=3, column=1)

    tk.Button(window, text="Submit", command=submit).grid(row=4, columnspan=2)

# Function to delete evidence
def delete_evidence():
    evidence_id = simpledialog.askstring("Input", "Enter Evidence ID to delete")
    result = db["evidence"].delete_one({"_id": ObjectId(evidence_id)})
    if result.deleted_count:
        messagebox.showinfo("Success", "Evidence deleted")
    else:
        messagebox.showerror("Error", "Evidence not found")

# Function to search evidence
def search_evidence():
    search_term = simpledialog.askstring("Input", "Enter search term (Evidence Type, Case ID, or Description)")
    evidence_list = db["evidence"].find({
        "$or": [
            {"type": {"$regex": search_term, "$options": "i"}},
            {"case_id": {"$regex": search_term, "$options": "i"}},
            {"description": {"$regex": search_term, "$options": "i"}},
        ]
    })
    
    if not evidence_list:
        messagebox.showerror("Error", "No evidence found")
        return

    window = tk.Toplevel(root)
    window.title("Search Results")
    
    tree = ttk.Treeview(window, columns=("type", "description", "case_id"), show="headings")
    for col in tree["columns"]:
        tree.heading(col, text=col)
    
    for evidence in evidence_list:
        file_name = "None"
        if evidence["file_id"]:
            file_data = fs.get(evidence["file_id"])
            file_name = file_data.filename
        tree.insert("", "end", values=(evidence["type"], evidence["description"], evidence["case_id"], file_name))
    
    tree.pack(fill="both", expand=True)

# Function to open Evidence Management menu
def evidence_menu():
    window = tk.Toplevel(root)
    window.title("Evidence Management")
    options = [
        ("Add Evidence", add_evidence),
        ("View Evidence", view_evidence),
        ("Update Evidence", update_evidence),
        ("Delete Evidence", delete_evidence),
        ("Search Evidence", search_evidence)
    ]
    for text, cmd in options:
        tk.Button(window, text=text, width=30, command=cmd).pack(pady=5)

def assign_officer():
    def submit():
        case_id = case_id_entry.get()
        officer_id = officer_id_entry.get()
        # Add assignment data to the database
        assignment_data = {
            "case_id": case_id,
            "officer_id": officer_id,
        }
        db["officer_assignments"].insert_one(assignment_data)
        messagebox.showinfo("Success", "Officer assigned successfully")
        window.destroy()

    window = tk.Toplevel(root)
    window.title("Assign Officer")
    
    # Create form fields
    tk.Label(window, text="Case ID").grid(row=0, column=0)
    tk.Label(window, text="Officer ID").grid(row=1, column=0)

    case_id_entry = tk.Entry(window)
    officer_id_entry = tk.Entry(window)

    case_id_entry.grid(row=0, column=1)
    officer_id_entry.grid(row=1, column=1)

    tk.Button(window, text="Submit", command=submit).grid(row=2, columnspan=2)

# Function to view officer assignments
def view_assignments():
    window = tk.Toplevel(root)
    window.title("View Officer Assignments")
    
    tree = ttk.Treeview(window, columns=("case_id", "officer_id"), show="headings")
    for col in tree["columns"]:
        tree.heading(col, text=col)
    
    for assignment in db["officer_assignments"].find():
        tree.insert("", "end", values=(assignment["case_id"], assignment["officer_id"]))
    
    tree.pack(fill="both", expand=True)

# Function to update officer assignment
def update_assignment():
    assignment_id = simpledialog.askstring("Input", "Enter Assignment ID to update")
    assignment = db["officer_assignments"].find_one({"_id": ObjectId(assignment_id)})
    
    if not assignment:
        messagebox.showerror("Error", "Assignment not found")
        return

    def submit():
        updated_data = {
            "case_id": case_id_entry.get(),
            "officer_id": officer_id_entry.get(),
        }

        db["officer_assignments"].update_one({"_id": ObjectId(assignment_id)}, {"$set": updated_data})
        messagebox.showinfo("Success", "Assignment updated successfully")
        window.destroy()

    window = tk.Toplevel(root)
    window.title("Update Officer Assignment")
    
    tk.Label(window, text="Case ID").grid(row=0, column=0)
    tk.Label(window, text="Officer ID").grid(row=1, column=0)

    case_id_entry = tk.Entry(window)
    officer_id_entry = tk.Entry(window)

    case_id_entry.insert(0, assignment["case_id"])
    officer_id_entry.insert(0, assignment["officer_id"])

    case_id_entry.grid(row=0, column=1)
    officer_id_entry.grid(row=1, column=1)

    tk.Button(window, text="Submit", command=submit).grid(row=2, columnspan=2)

# Function to delete officer assignment
def delete_assignment():
    assignment_id = simpledialog.askstring("Input", "Enter Assignment ID to delete")
    result = db["officer_assignments"].delete_one({"_id": ObjectId(assignment_id)})
    if result.deleted_count:
        messagebox.showinfo("Success", "Assignment deleted")
    else:
        messagebox.showerror("Error", "Assignment not found")

# Function to search officer assignments
def search_assignments():
    search_term = simpledialog.askstring("Input", "Enter search term (Case ID or Officer ID)")
    assignment_list = db["officer_assignments"].find({
        "$or": [
            {"case_id": {"$regex": search_term, "$options": "i"}},
            {"officer_id": {"$regex": search_term, "$options": "i"}},
        ]
    })
    
    if not assignment_list:
        messagebox.showerror("Error", "No assignments found")
        return

    window = tk.Toplevel(root)
    window.title("Search Results")
    
    tree = ttk.Treeview(window, columns=("case_id", "officer_id"), show="headings")
    for col in tree["columns"]:
        tree.heading(col, text=col)
    
    for assignment in assignment_list:
        tree.insert("", "end", values=(assignment["case_id"], assignment["officer_id"]))
    
    tree.pack(fill="both", expand=True)

# Function to open Officer Assignment menu
def officer_assignment_menu():
    window = tk.Toplevel(root)
    window.title("Officer Assignment Management")
    options = [
        ("Assign Officer", assign_officer),
        ("View Assignments", view_assignments),
        ("Update Assignment", update_assignment),
        ("Delete Assignment", delete_assignment),
        ("Search Assignments", search_assignments)
    ]
    for text, cmd in options:
        tk.Button(window, text=text, width=30, command=cmd).pack(pady=5)

def generate_criminal_report():
    criminals_data = list(criminals.find())  # Convert cursor to list

    if not criminals_data:
        messagebox.showinfo("Report", "No criminals found.")
        return

    report_text = "Criminal Report:\n\n"
    for criminal in criminals_data:
        report_text += f"Custom ID: {criminal['custom_id']}\n"
        report_text += f"Name: {criminal['name']}\n"
        report_text += f"Age: {criminal['age']}\n"
        report_text += f"Gender: {criminal['gender']}\n"
        report_text += f"Crime: {criminal['crime']}\n"
        report_text += f"Status: {criminal['status']}\n\n"

    report_window = tk.Toplevel(root)
    report_window.title("Criminal Report")
    report_label = tk.Label(report_window, text=report_text, justify="left")
    report_label.pack(padx=10, pady=10)

def generate_case_report():
    cases_data = []
    for case in cases.find():
        case_data = {
            "case_id": case["case_id"],
            "description": case["description"],
            "status": case["status"],
            "officer": case["officer"],
        }
        cases_data.append(case_data)

    if not cases_data:
        messagebox.showinfo("Report", "No cases found.")
        return

    report_text = "Case Report:\n\n"
    for case in cases_data:
        report_text += f"Case ID: {case['case_id']}\n"
        report_text += f"Description: {case['description']}\n"
        report_text += f"Status: {case['status']}\n"
        report_text += f"Officer: {case['officer']}\n"
        report_text += "\n"

    report_window = tk.Toplevel(root)
    report_window.title("Case Report")
    report_label = tk.Label(report_window, text=report_text, justify="left")
    report_label.pack(padx=10, pady=10)

def generate_officer_report():
    officer_assignments = db["officer_assignments"].find()
    report_text = "Officer Report:\n\n"

    for assignment in officer_assignments:
        case = cases.find_one({"case_id": assignment["case_id"]})
        if case:
            report_text += f"Officer ID: {assignment['officer_id']}\n"
            report_text += f"Assigned Case ID: {case['case_id']}\n"
            report_text += f"Description: {case['description']}\n"
            report_text += f"Status: {case['status']}\n\n"

    if not report_text.strip():
        messagebox.showinfo("Report", "No officer assignments found.")
        return

    report_window = tk.Toplevel(root)
    report_window.title("Officer Report")
    report_label = tk.Label(report_window, text=report_text, justify="left")
    report_label.pack(padx=10, pady=10)

def reports_legal_menu():
    window = tk.Toplevel(root)
    window.title("Reports & Legal")
    options = [
        ("Generate Criminal Report", generate_criminal_report),
        ("Generate Case Report", generate_case_report),
        ("Generate Officer Report", generate_officer_report),
    ]
    for text, cmd in options:
        tk.Button(window, text=text, width=30, command=cmd).pack(pady=5)

def reports_legal_menu():
    window = tk.Toplevel(root)
    window.title("Reports & Legal")
    options = [
        ("Generate Criminal Report", generate_criminal_report),
        ("Generate Case Report", generate_case_report),
        ("Generate Officer Report", generate_officer_report),
    ]
    for text, cmd in options:
        tk.Button(window, text=text, width=30, command=cmd).pack(pady=5)

def main_menu():
    tk.Label(root, text="Crime Analysis System", font=("Arial", 18)).pack(pady=20)
    tk.Button(root, text="Criminal Management", width=30, command=criminal_menu).pack(pady=10)
    tk.Button(root, text="Case Management", width=30, command=case_menu).pack(pady=10)
    tk.Button(root, text="Victim & Witness Management", width=30, command=victim_witness_menu).pack(pady=10)
    tk.Button(root, text="Evidence Management", width=30, command=evidence_menu).pack(pady=10)
    tk.Button(root, text="Officer Assignment", width=30, command=officer_assignment_menu).pack(pady=10)
    tk.Button(root, text="Reports & Legal", width=30, command=reports_legal_menu).pack(pady=10)
    tk.Button(root, text="Exit", width=30, command=root.quit).pack(pady=10)

main_menu()
root.mainloop()