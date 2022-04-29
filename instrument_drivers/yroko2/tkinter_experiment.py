# Import module 
from tkinter import *
  
# Create object 
root = Tk()
  
# Adjust size 
root.geometry("720x480")
  
# Add image file
bg = PhotoImage(file = "background.png")
  
# Show image using label
label1 = Label( root, image = bg)
label1.place(x = 0, y = 0)
  
# label2 = Label( root, text = "Welcome")
# label2.pack(pady = 50)
  
# # Create Frame
# frame1 = Frame(root)
# frame1.pack(pady = 20 )
  
# # Add buttons
# button1 = Button(frame1,text="Exit")
# button1.pack(pady=20)
  
# button2 = Button( frame1, text = "Start")
# button2.pack(pady = 20)
  
# button3 = Button( frame1, text = "Reset")s
# button3.pack(pady = 20)
def on_press():
	print("pressed!")

up_button = PhotoImage(file='up_button.png')
button2= Button(root, image=up_button, command=on_press, height=10, width=10)
button2.place(x=197, y=303)
  
# Execute tkinter
root.mainloop()

