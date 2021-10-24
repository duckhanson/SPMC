#main.py

from flask import Flask
from flask import request
from flask_cors import CORS
# import sys
# sys.path.append('../algorithm/py4dbp')
# from py4dbp import Packer, Bin, Item
# import main as pm 
import json
import uuid
import configparser
from flask import send_file
import os

#===========================================================
#Gobal variable
#===========================================================
#RESULT_JSON_INFOS=[]
PALLET_WEIGHT_LIMMIT=450  #kg
MAX_CONTAINER_HEIGHT=225 #cm
#============================================================
#Gobal config
#============================================================
app=Flask(__name__)
#cors problem
CORS(app, resources={r"/api/*": {"origins": "*"}})
CORS(app, resources={r"/get_resource/*": {"origins": "*"}})
#upload setting
config=configparser.ConfigParser()
config.read("cgi_config.ini")
app.config['UPLOAD_FOLDER']=config['DEFAULT']['UPLOAD_FOLDER']
app.config['MAX_CONTENT_LENGTH']=config['DEFAULT']['MAX_CONTENT_LENGTH']
ALLOWED_EXTENSIONS=set(['xlsx','xls'])
#==================================``===========================
#Function Name: Processsing3DBP
#Description: convert box_info and container info 
#EXAMPLE: HOW STRUCTURE LOOKS LIKE
'''
{
status: 0, 1, 2 //0:success, 1:fail, 2: partial success 3: critical error 
containers:{
	container1:{
	...informations
		fit_box:{	
		}
		unfit_box:{
		}
	},
	container2:{
		fit_box{
			box_infos
		}
		unfit_box:{
		}
	}
}
}
'''
#=============================================================
def Processing3DBP(container_infos, box_infos):
    packer = Packer()
    # print(f'{packer=}')
    #0:success, 1:fail, 2:partial sucess 3:critical error

    flag_success=True
    flag_partial_success=False
    

    total_container_types=len(container_infos)
    total_box_types=len(box_infos)


    #pack box_info
    for index, box_info in enumerate(box_infos):
        #if the sameType of box only is one, do nothing and pass it to algorithm
        packer.add_item(Item(box_info['ID'], box_info['name_with_index'], int(box_info['X']), int(box_info['Y']), int(box_info['Z']), int(box_info['Weight']), box_info['TypeIndex']))
    

    #processing container_info
    for index, container_info in enumerate(container_infos):
        packer.add_bin(Bin(container_info['ID'],
        container_info['name_with_index'],
        int(container_info['X']),
        int(container_info['Y']),
        int(container_info['Z']),
        int(container_info['Weight_limmit']),
        container_info['TypeIndex']     
             ))
   
    #calculate
    packer.pack()

    containers_array=[]
    statusNumber=-1

    for b in packer.bins:
        #if there if unfitted_item
        if len(b.unfitted_items)!=0:
            flag_success=False
        if len(b.items)!=0:
            flag_partial_success=True
        #result_json_info=json.dumps(b.getResultDictionary(), indent=4)
        containers_array.append(b.getResultDictionary())

    #add statusNumber
    statusNumber=None
    if(flag_success==True):
        #allsuccess
        statusNumber=1
    elif(flag_success==False and flag_partial_success==True):
        #partial success
        statusNumber=3
    else:
        #fail
        statusNumber=2

    #add status of containers
    final_info_dictionary={
        "status":statusNumber,
        "containers":containers_array,
        "total_container_types":total_container_types,
        "total_box_types":total_box_types
        }

    result_json_info=json.dumps(final_info_dictionary, indent=4)
 

        
        #print(b.getResultDictionary())
    
    # print(result_json_info)
    return result_json_info





#===============================================================================
#FunctinoName: Processing3DBPwithPallet
#Description :Base on Processing3DBP
#==========================================================================
def Processing3DBPWithPallet(container_infos, box_infos, pallet_infos):

    virtual_container_with_packed_box_array=[]
    #return the containers with packed information
    packer = Packer()
    #0:success, 1:fail, 2:partial sucess 3:critical error
    statusNumber=-1000
    pallet_status_number=-1000
    flag_success_pallet=True
    flag_partial_success_pallet=False
    

    total_container_types=len(container_infos)
    total_box_types=len(box_infos)
    total_pallet_types=len(pallet_infos)


    #dictionary for searching pallet and virtual container pair
    id_to_pallet=None


    #pack box_info
    for index, box_info in enumerate(box_infos):
        #if the sameType of box only is one, do nothing and pass it to algorithm
        packer.add_item(Item(box_info['ID'], box_info['name_with_index'], box_info['X'], box_info['Y'], box_info['Z'], box_info['Weight'],box_info['TypeIndex']))
    

    #sort the pallet_infos base on area, from large to small
    pallet_infos=sorted(pallet_infos, key=lambda pallet_info: pallet_info["X"]* pallet_info["Z"], reverse=True)
    ids=[pallet_info['ID'] for pallet_info in pallet_infos]
    id_to_pallet=dict(zip(ids, pallet_infos))

    virtual_containers=[]

    ids_of_box=[box['ID'] for box in box_infos]
    id_to_box=dict(zip(ids_of_box, box_infos))

    #create the virtual container to pack, virtual container is the space upon
    for index, pallet_info in enumerate(pallet_infos):
        virtual_container=pallet_info.copy()
        virtual_container["Weight_limmit"]=PALLET_WEIGHT_LIMMIT-pallet_info["Weight"]
        virtual_container["Y"]=MAX_CONTAINER_HEIGHT-pallet_info["Y"]
        virtual_container["Total_box_weight"]=0
        #pack all remain box into one container at once
        packer.add_bin(Bin(virtual_container['ID'],
        virtual_container['name_with_index'], 
        virtual_container['X'],
        virtual_container['Y'],
        virtual_container['Z'],
        virtual_container['Weight_limmit'],
        virtual_container['TypeIndex']
        ))
        packer.pack(bigger_first=True)
        for b in packer.bins:
            if len(b.unfitted_items)!=0:
                flag_success_pallet=False
            if len(b.items)!=0:
                total_weight=0
                for i in b.items:
                    total_weight+=i.weight
                virtual_container["Total_box_weight"]=total_weight
                flag_partial_success_pallet=True
            virtual_container_with_packed_box_array.append(b.getResultDictionary())
        virtual_containers.append(virtual_container)
        #all remain box have been packed
        if len(b.unfitted_items)==0:
            break
        else:
            print("!!!!!!!!!!!!!!!!!!!!find unfitted_items")
            packer=Packer()
            for box_info in b.get_unfitted_items_as_dict_array():
                name_with_index= id_to_box[box_info['ID']]['name_with_index']
                packer.add_item(Item(box_info['ID'], name_with_index, box_info['X'], box_info['Y'], box_info['Z'], box_info['Weight'],box_info['TypeIndex']))


    #find virtual container by ID
    id_to_virtualcontainer=dict(zip(ids, virtual_containers))

    if(flag_success_pallet==True):
        #allsuccess
        pallet_status_number=10
    elif(flag_success_pallet==False and flag_partial_success_pallet==True):
        #partial success
        pallet_status_number=30
    else:
        #fail
        pallet_status_number=20

    #pack virtual container into real container
    status_number=-1000

    flag_success=True
    flag_partial_success=False

    packer=Packer(TWO_D_MODE=True)
    remain_container_infos=container_infos
    containers_array=[]
    packed_pallet_infos=[]


    for virtual_container in virtual_container_with_packed_box_array:
        pallet=id_to_pallet[virtual_container['ID']]
        pallet['Fitted_items']=virtual_container['Fitted_items']
        pallet['Weight']=id_to_virtualcontainer[virtual_container['ID']]['Total_box_weight']+pallet['Weight']
        packed_pallet_infos.append(pallet)

    print(packed_pallet_infos)

    for packed_pallet_info in packed_pallet_infos:
        packer.add_item(Item(
        packed_pallet_info['ID'],
        packed_pallet_info['name_with_index'], 
        packed_pallet_info['X'],
        packed_pallet_info['Y'],
        packed_pallet_info['Z'],
        packed_pallet_info['Weight'],
        packed_pallet_info['TypeIndex'],
        packed_pallet_info['Fitted_items']
        ))


    if len(remain_container_infos) >0:
        container_info=remain_container_infos.pop(0)
        packer.add_bin(Bin(container_info['ID'],
        container_info['name_with_index'],
        container_info['X'],
        container_info['Y'],
        container_info['Z'],
        container_info['Weight_limmit'],
        container_info['TypeIndex']
        ))
        packer.pack()
        b=packer.bins[0]


        #there is a bug need to be fix, maybe i didn't modify the algorithm right, there will have unfitted item even
        # the result totally packed, the following is a mitigration way at present 
        b.unfitted_items=[]
        containers_array.append(b.getResultDictionary())
        print(b.getResultDictionary())

    else:
        #error
        statusNumber=300+pallet_status_number


    statusNumber=100+pallet_status_number

    #add status of containers
    final_info_dictionary={
        "status":statusNumber,
        "total_container_types":total_container_types,
        "total_pallet_types":total_pallet_types,
        "total_box_types":total_box_types,
        "containers":containers_array,
        }

    result_json_info=json.dumps(final_info_dictionary, indent=4)
 

        
        #print(b.getResultDictionary())
    print(result_json_info)
    return result_json_info



#==============================================================
#Function Name: CheckValidJsonData
#Descritpion: Check whether the json file is in the format we want
#Return: if the result is valid return true else false
#==============================================================
# TO DO!
def CheckValidJsonData(infoJsonData):
    FirstLayerKeys={'containers':False,'box':False}
    containers_sec_key={'ID':False,'TypeName':False,'X':False,'Y':False,'Z':False,'Weight_limmit':False,'Numbers':False}
    box_sec_key={'ID':False,'TypeName':False,'X':False, 'Y':False, 'Z':False, 'Weight':False, 'Numbers':False}

    firstkyes=infoJsonData.keys()
    #for key in FirstLayerKeys.keys():
#=============================================================
#
#
#=============================================================
@app.errorhandler(404)
def page_not_found(error):
   return "404 not found"
    
#=============================================================
#Function:testImg
#
#=============================================================
@app.route('/get_resource/image/<filename>', methods=['GET'])
def get_image(filename):
    filepath="./textures/"+filename
    if os.path.isfile(filepath):
        return send_file(filepath, mimetype='image/gif')
    else:
        return "404 not found"


#==============================================================
#Function Name:Index Page
#Description: used in connnection test
#==============================================================
@app.route('/api/',methods=['GET'])
def IndexPage():
    return "hello"


#===============================================================
#Function Name: upLoadFile()
#Description: handle the file that need to be upload
# the relevent config setting written in cgi_config_ini
# ===============================================================
@app.route('/api/uploadExcelSettingFile',methods=['POST'])
def upLoadExcelSettingFile():
    file=request.files['file']




#===============================================================
#Funciton Name: reciveJsonFromClient
#Description: recive the post data which content the box_info and container_info
#return: the return value send back to server side will contenet with
#data that going to be render in 3d.
#===============================================================
@app.route('/api/recv/3dbinpack/info',methods=['POST'])
def reciveJsonFromClient():
    info_jsondata=request.get_json(force=True)
    #print(info_jsondata)
    #retrive data from json
    container_infos=info_jsondata['containers']
    box_infos=info_jsondata['boxes']
    pallet_infos=info_jsondata['pallets']


    #preprocess the data
    container_infos=preProcessContainerInfos(container_infos)

    #sorted by volume
    box_infos=sorted(box_infos,  key=lambda box_info: int(box_info["X"])* int(box_info["Z"])*int(box_info['Y']), reverse=True)

    box_infos=preProcessBoxInfos(box_infos)
    #pallet mode
    if info_jsondata['pallet_mode']==1:
        print("Pallet mode on")
        pallet_infos=preProcessBoxInfos(pallet_infos)
        jsonData=Processing3DBPWithPallet(container_infos, box_infos, pallet_infos)
    #none pallet mode
    else:
        #print(box_infos)
        jsonData=Processing3DBP(container_infos, box_infos)
    return jsonData
#==================================================================
#Function: PreProcessContainerInfos
#Description: expand the same type of Object
#example: box1 with numbers=3 => [box1, box1, box1]
#==================================================================
def preProcessContainerInfos(container_infos):
    preProcessedInfo=[]
    for container_type_index, container_info in enumerate(container_infos):
        new_container_info={}
        #if the sameType of container number only is one, do nothing and pass it to algorithm
        if (container_info['Numbers'] ==1):
            container_info['TypeIndex']=1
            container_info['name_with_index']=container_info['TypeName']+"_0"
            preProcessedInfo.append(container_info)
        #else multiple numbers condition, create copy and pass it into algorithm
        else:
            #create the numbers of clone
            for number_index in range(0, int(container_info['Numbers'])):
                new_container_info=container_info.copy()
                new_container_info['name_with_index']=container_info['TypeName']+"_"+str(number_index)
                new_container_info['TypeIndex']=container_type_index
                #create new uuid expect index 0
                if number_index!=0:
                    new_container_info['ID']=str(uuid.uuid4())
                preProcessedInfo.append(new_container_info)
    #print(preProcessedInfo)
    return preProcessedInfo







#=====================================================================
# py3dbp
# Description
#=====================================================================



from flask.typing import TeardownCallable
from werkzeug.wrappers import response
from constants import RotationType, Axis
from auxiliary_methods import intersect, set_to_decimal



DEFAULT_NUMBER_OF_DECIMALS = 3
START_POSITION = [0, 0, 0]


class Item:
    def __init__(self,ID ,name, width, height, depth, weight, type_index, Fitted_items=None):
        self.ID=ID
        self.name = name
        self.__width = int(width)
        self.__height = int(height)
        self.__depth = int(depth)
        self.weight = int(weight)
        self.__area = int(depth) * int(width)
        self.rotation_type = 0
        self.position = START_POSITION
        self.number_of_decimals = DEFAULT_NUMBER_OF_DECIMALS
        self.type_index=type_index
        self.Fitted_items=Fitted_items

    def get_width(self):
        return self.__width

    def get_height(self):
        return self.__height
    
    def get_depth(self):
        return self.__depth
    
    def get_area(self):
        return self.__area
    
    def set_width(self, val):
        self.__width = val
        self.update_area()

    def set_height(self, val):
        self.__height = val
        self.update_area()
    
    def set_depth(self, val):
        self.__depth = val
        self.update_area()

    def update_area(self):
        self.__area = self.__width * self.__depth
    

    def rotate_width_height(self):
        self.__width, self.__height = self.__height, self.__width
        # print("Rotate width_depth(area change)")
        self.update_area()
    
    def rotate_width_depth(self):
        self.__width, self.__depth = self.__depth, self.__width
        # print("Rotate width_depth(area not change)")
        self.update_area()
    
    def rotate_height_depth(self):
        self.__height, self.__depth = self.__depth, self.__height
        # print("Rotate width_depth(area change)")
        self.update_area()
    
    def rotate(self, rtt):
        if rtt == 0:
            # (max area) depth > width > height
            return
        elif rtt == 1:
            # rotate width & depth (max area)
            self.rotate_width_depth()
        elif rtt == 2:
            # rotate depth & height (second big area)
            self.rotate_height_depth()
        elif rtt == 3:
            # rotate width & depth (second big area)
            self.rotate_width_depth()
        elif rtt == 4:
            # rotate depth & height (third big area)
            self.rotate_height_depth()
        elif rtt == 5:
            # rotate width & depth (third big area)
            self.rotate_width_depth()
        

    def format_numbers(self, number_of_decimals):
        self.__width = set_to_decimal(self.__width, number_of_decimals)
        self.__height = set_to_decimal(self.__height, number_of_decimals)
        self.__depth = set_to_decimal(self.__depth, number_of_decimals)
        self.weight = set_to_decimal(self.weight, number_of_decimals)
        self.number_of_decimals = number_of_decimals

    def string(self):
        return f"""
        {self.name}:       
            ID:{self.ID}
            X:{self.width}, 
            Y:{self.height}, 
            Z:{self.depth}, 
            Weight:{self.weight}
            rotation:{self.rotation_type}
            position:{self.position}
        """
        #we have to covert the Decimal object to float so that
        #java packer will be happy
    def getResultDictionary(self):
        #conver position information into float

        if self.Fitted_items!=None:
            return{"ID":self.ID,
            "TypeName":self.name,
            "X":float(self.__width),
            "Y":float(self.__height),
            "Z":float(self.__depth), 
            "Weight":float(self.weight),
            "position_x":float(self.position[0]),
            "position_y":float(self.position[1]),
            "position_z":float(self.position[2]),
            "RotationType":self.rotation_type,
            "TypeIndex":self.type_index,
            "Fitted_items":self.Fitted_items
            }
        else:
            return{"ID":self.ID,
            "TypeName":self.name,
            "X":float(self.__width),
            "Y":float(self.__height),
            "Z":float(self.__depth), 
            "Weight":float(self.weight),
            "position_x":float(self.position[0]),
            "position_y":float(self.position[1]),
            "position_z":float(self.position[2]),
            "RotationType":self.rotation_type,
            "TypeIndex":self.type_index,
            }

    def get_volume(self):
        return set_to_decimal(
            self.__width * self.__height * self.__depth, self.number_of_decimals
        )

    def get_dimension(self):
        if self.rotation_type == RotationType.RT_WHD:
            dimension = [self.__width, self.__height, self.__depth]
        elif self.rotation_type == RotationType.RT_HWD:
            dimension = [self.__height, self.__width, self.__depth]
        elif self.rotation_type == RotationType.RT_HDW:
            dimension = [self.__height, self.__depth, self.__width]
        elif self.rotation_type == RotationType.RT_DHW:
            dimension = [self.__depth, self.__height, self.__width]
        elif self.rotation_type == RotationType.RT_DWH:
            dimension = [self.__depth, self.__width, self.__height]
        elif self.rotation_type == RotationType.RT_WDH:
            dimension = [self.__width, self.__depth, self.__height]
        else:
            dimension = []

        return dimension


class Bin:
    def __init__(self, ID, name, width, height, depth, max_weight, type_index, weight = 0):
        self.ID=ID
        self.name = name
        self.width = int(width)
        self.height = int(height)
        self.depth = int(depth)
        self.weight = int(weight)
        self.container_type = 0
        if weight != 0:
            # this is a pallet
            self.container_type = 1
        self.max_weight = int(max_weight)
        self.items = []
        self.unfitted_items = []
        self.number_of_decimals = DEFAULT_NUMBER_OF_DECIMALS
        self.type_index=type_index

    def format_numbers(self, number_of_decimals):
        self.width = set_to_decimal(self.width, number_of_decimals)
        self.height = set_to_decimal(self.height, number_of_decimals)
        self.depth = set_to_decimal(self.depth, number_of_decimals)
        self.max_weight = set_to_decimal(self.max_weight, number_of_decimals)
        self.number_of_decimals = number_of_decimals

    def get_unfitted_items_as_dict_array(self):
        unFittedItemArray=[]
        for unfitted_item in self.unfitted_items:
            unFittedItemArray.append(unfitted_item.getResultDictionary())
        return unFittedItemArray
        
    def string(self):
        return f"""
            ID:{self.ID},
            TypeName:{self.name},
            X:{float(self.width)}, 
            Y:{float(self.height)}, 
            Z:{float(self.depth)}, 
            Weight_limmit:{float(self.max_weight)}
        """
    def getResultDictionary(self):
        #convet Fitted_items to dictionary(array of dics)
        FittedItemArray=[]
        for fitted_item in self.items:
            FittedItemArray.append(fitted_item.getResultDictionary())
        

        unFittedItemArray=[]
        #convert unfitted_items to array of dictionary
        for unfitted_item in self.unfitted_items:
            unFittedItemArray.append(unfitted_item.getResultDictionary())


        return{
            "ID":self.ID,
            "TypeName":self.name,
            "TypeIndex":self.type_index,
            "X":float(self.width),
            "Y":float(self.height),
            "Z":float(self.depth),
            "Weight_limmit":float(self.max_weight),
            "Fitted_items":FittedItemArray,
            "UnFitted_items":unFittedItemArray,
    }

    def get_volume(self):
        return set_to_decimal(
            self.width * self.height * self.depth, self.number_of_decimals
        )

    def get_total_weight(self):
        total_weight = 0

        for item in self.items:
            total_weight += item.weight

        return set_to_decimal(total_weight, self.number_of_decimals)

    def put_item(self, item, pivot):
        fit = False
        valid_item_position = item.position
        item.position = pivot

        for i in range(0, len(RotationType.ALL)):
            item.rotation_type = i
            dimension = item.get_dimension()
            if (
                self.width < pivot[0] + dimension[0] or
                self.height < pivot[1] + dimension[1] or
                self.depth < pivot[2] + dimension[2]
            ):
                continue

            fit = True

            for current_item_in_bin in self.items:
                if intersect(current_item_in_bin, item):
                    fit = False
                    break

            if fit:
                if self.get_total_weight() + item.weight > self.max_weight:
                    fit = False
                    return fit

                self.items.append(item)

            if not fit:
                item.position = valid_item_position

            return fit

        if not fit:
            item.position = valid_item_position

        return fit

    def put_item_only_2D_rotate(self, item, pivot):
        fit = False
        valid_item_position = item.position
        item.position = pivot

        for i in range(0, len(RotationType.TWO_D)):
            item.rotation_type = RotationType.TWO_D[i]
            dimension = item.get_dimension()
            if (
                self.width < pivot[0] + dimension[0] or
                self.height < pivot[1] + dimension[1] or
                self.depth < pivot[2] + dimension[2]
            ):
                continue

            fit = True

            for current_item_in_bin in self.items:
                if intersect(current_item_in_bin, item):
                    fit = False
                    break

            if fit:
                if self.get_total_weight() + item.weight > self.max_weight:
                    fit = False
                    return fit

                self.items.append(item)

            if not fit:
                item.position = valid_item_position

            return fit

        if not fit:
            item.position = valid_item_position

        return fit



class Packer:
    def __init__(self, TWO_D_MODE=False):
        self.bins = []
        self.items = []
        self.unfit_items = []
        self.total_items = 0
        self.TWO_D_MODE=TWO_D_MODE
        # print("Packer init")

    def add_bin(self, bin):
        # print("add bin")
        return self.bins.append(bin)

    def add_item(self, item):
        self.total_items = len(self.items) + 1

        return self.items.append(item)

    def pack_to_bin(self, bin, item):
        fitted = False
        if not bin.items:
            if self.TWO_D_MODE:
                response=bin.put_item_only_2D_rotate(item, START_POSITION)
            response = bin.put_item(item, START_POSITION)

            if not response:
                bin.unfitted_items.append(item)

            return

        for axis in range(0, 3):
            items_in_bin = bin.items

            for ib in items_in_bin:
                pivot = [0, 0, 0]
                w, h, d = ib.get_dimension()
                if axis == Axis.WIDTH:
                    pivot = [
                        ib.position[0] + w,
                        ib.position[1],
                        ib.position[2]
                    ]
                elif axis == Axis.HEIGHT:
                    pivot = [
                        ib.position[0],
                        ib.position[1] + h,
                        ib.position[2]
                    ]
                elif axis == Axis.DEPTH:
                    pivot = [
                        ib.position[0],
                        ib.position[1],
                        ib.position[2] + d
                    ]


                if self.TWO_D_MODE:
                    if bin.put_item_only_2D_rotate(item, pivot):
                        fitted = True
                        break
                else:
                    if bin.put_item(item, pivot):
                        fitted = True
                        break
            if fitted:
                break

        if not fitted:
            bin.unfitted_items.append(item)
            
    def pack_to_bin_self_def(self, pos, limit_d, limit_w, Items, num_items, bin):
        if(num_items == 0):
            return

        vsp = [pos]
        #put in Bin
        next_board = []
        remain_items = []
        for i in range(len(Items)):
            # if Items[i].weight + bin.weight > bin.max_weight:
            #     continue
            pos_erase = -1
            p = [-1,-1,-1]
            p1 = [-1,-1,-1]
            p2 = [-1,-1,-1]
            for pos_i in range(len(vsp)):
                # find valid start position
                # already_put = False
                # for rtt in range(6):
                #     if already_put:
                #         break
                    # Items[i].rotate(rtt)
                if Items[i].get_depth() <= limit_d and Items[i].get_width() <= limit_w and vsp[pos_i][0] + Items[i].get_depth() <= bin.depth and vsp[pos_i][1] + Items[i].get_width() <= bin.width and vsp[pos_i][2] + Items[i].get_height() <= bin.height:
                    pos_erase = pos_i
                    p = vsp[pos_i]
                    # print(f'{p=}')
                    Items[i].position = [p[1], p[2], p[0]]
                    # print(f'{Items[i].position=}')
                    bin.put_item(Items[i], Items[i].position)
                    bin.weight += Items[i].weight
                    # print(str(Items[i].ID) + ": " + str(Items[i].position))
                    next_board.append([[p[0], p[1], p[2] + Items[i].get_height()], Items[i].get_depth(), Items[i].get_width()])
                    p1 = [p[0] + Items[i].get_depth(), p[1], p[2]]
                    p2 = [p[0], p[1] + Items[i].get_width(), p[2]]
                    break
                        # already_put = True
                # if already_put:
                #     break
                

            if pos_erase != -1:    
                vsp.pop(pos_erase)
                vsp.append(p1)
                vsp.append(p2)
            else:
                remain_items.append(Items[i])

        if len(remain_items) == num_items:
            for it in remain_items: 
                bin.unfitted_items.append(it)
            return

        num_items = len(remain_items)
        for b in next_board:
            self.pack_to_bin_self_def(b[0], b[1], b[2], remain_items, num_items, bin)

    def pack(
        self, bigger_first=False, distribute_items=False,
        number_of_decimals=DEFAULT_NUMBER_OF_DECIMALS
    ):
        # print("into pack()")
        for bin in self.bins:
            bin.format_numbers(number_of_decimals)

        for item in self.items:
            item.format_numbers(number_of_decimals)

        self.bins.sort(
            key=lambda bin: bin.get_volume(), reverse=bigger_first
        )
        self.items.sort(
            key=lambda item: item.get_volume(), reverse=bigger_first
        )
        for it in self.items:
            l = [it.get_width(), it.get_height(), it.get_depth()]
            l.sort()
            it.set_height(l[0])
            it.set_width(l[1])
            it.set_depth(l[2])

            # print(f"{it.get_width()=}")
            # print(f"{it.get_height()=}")
            # print(f"{it.get_depth()=}")


        self.items.sort(key = lambda s: s.get_area(), reverse = True)
        # print(f'{self.bins=}')
        for bin in self.bins:
            self.pack_to_bin_self_def(START_POSITION, bin.depth, bin.width, self.items, len(self.items), bin)

            if distribute_items:
                for item in bin.items:
                    self.items.remove(item)







#=====================================================================
#Function name
#Description
#=====================================================================
def preProcessBoxInfos(box_infos):
    return preProcessContainerInfos(box_infos)

if __name__=="__main__":
    app.run()
