import os
from pathlib import Path
import json

class FileUtility:
    
    @staticmethod
    def readFile(file_path):
        if FileUtility.checkIfFileExists(file_path)["data"]:
            with open(file_path, 'r+') as file:
                return {"log":None, "data": file.read()}
        else:
            return {"log":f"File does not exists for reading the file: {file_path}", "data": None}
    
    @staticmethod
    def deleteFile(file_path):
        try:
            if os.path.exists(file_path):
                    os.remove(file_path)
                    return {"log":None, "data": True}
            else:
                return {"data":False, "log": f"{file_path} does not exist."}
        except Exception as e:
            return {"data":False, "log": (f"Error deleting file {file_path}. ", e)}
            
    @staticmethod
    def writeFile(file_path, data):   
             
        if FileUtility.createDirectoryIfNotExists(file_path)["data"]:
            try:
                with open(file_path, "w+") as file:
                    file.write(str(data))
                    return {"data":True, "log": (f"{file_path} has been written.")}
    
            except Exception as e:
                return {"data":False, "log": (f"Error writing file {file_path}. ", e)}
                
    @staticmethod
    def appendFile(file_path, data):   
        if FileUtility.createDirectoryIfNotExists(file_path)["data"]:
            try:
                with open(file_path, "a+") as file:
                    file.write(str(data))
                    return {"data":True, "log": (f"{file_path} has been appended.")}
    
            except Exception as e:
                return {"data":False, "log": (f"Error appending file {file_path}. ", e)}
            
    @staticmethod
    def updateJsonObjectFile(file_path, key, value):
        try:
            # Step 1: Read existing content (if any)
            json_data = {}
            read_result = FileUtility.readFile(file_path)
            if read_result["data"]:
                try:
                    json_data = json.loads(read_result["data"])
                except json.JSONDecodeError:
                    return {"data": False, "log": f"Invalid JSON in {file_path}."}

            # Step 2: Update or insert the key
            json_data[key] = value

            # Step 3: Save back the updated dictionary
            with open(file_path, "w") as f:
                json.dump(json_data, f, indent=4)
            return {"data": True, "log": f"Key '{key}' updated in {file_path}."}

        except Exception as e:
            return {"data": False, "log": f"Error updating key in JSON file: {e}"}
            
    @staticmethod
    def createDirectoryIfNotExists(file_path):
        # Check if the directory exists, and if not, create it
        try:
            if FileUtility.checkIfDirectoryExists(file_path)["data"] is False:
                directory = os.path.dirname(file_path)
                os.makedirs(directory)
            return {"data":True, "log": None       }
        except Exception as e:
            return {"data":False, "log": (f"Unable to access directory for {file_path}. Error: ",e)}
    
    @staticmethod
    def checkIfDirectoryExists(file_path):
        try:
            directory = os.path.dirname(file_path)
            if os.path.exists(directory):
                return {"log":True, "data": True}
        except Exception as e:
            return {"data":False, "log": (f"Unable to access directory for {file_path}. Error: ",e)}
            
        return {"log":False, "data": False}
    
    @staticmethod
    def checkIfFileExists(file_path):
        try:
            path = Path(file_path)
            if path.parent.exists():
                if path.exists():
                    return {"data":True, "log": None }
        except Exception as e:
            return {"data":False, "log": (f"Unable to access directory for {file_path}. Error: ",e)}
        return {"data":False, "log": None}