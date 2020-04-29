import os
import _alembic_hom_extensions as _abc
import numpy as np
try:
    from hou import ui
except:
    ui = None
_AbcModule = __import__("_alembic_hom_extensions")

def selFile():
    return hou.ui.selectFile(start_directory='$HIP',file_type = hou.fileType.Geometry,title = 'Select ABC Camera File')
class ImportABC:
    def __init__(self,seletFile):
        self.camList = []
        self.camPath = []
        self.file = seletFile
        if len(self.file)>0:
            self.filePath = hou.hscriptStringExpression(self.file)
            self.turn = self.BuildHierarchyRoot()
            if self.turn:
                self.abcTreeAll = _AbcModule.alembicGetSceneHierarchy(self.filePath,'')
                self.abcTreePath = _AbcModule.alembicGetObjectPathListForMenu(self.filePath)
                self.getABCCamTree(self.abcTreeAll)

#-------------------------------------------------
    def getABCCamTree(self,abcTreeAll):
        nodeName = abcTreeAll[0]
        nodeType = abcTreeAll[1]
        nodeChildren = abcTreeAll[2]
        if nodeType == 'camera':
            self.camList.append(nodeName) 
            for x in self.abcTreePath:
                if nodeName in x:
                    camlipath = x
            if camlipath not in self.camPath:
                self.camPath.append(camlipath)
            
        else : 
            for children in nodeChildren:
                self.getABCCamTree(children)
#-------------------------------------------------   
    def getCamList(self):
        if self.turn:
            index = hou.ui.selectFromList(self.camList,title = 'Select Camera Node')
            camlist = [self.camPath[i] for i in index] 
            return camlist
    
    def BuildHierarchyRoot(self): 
        fileName = self.filePath 
        if 'abc' not in fileName:
            if ui:
                ui.displayMessage(title='No Filename',
                    text='Please enter an Alembic file to load.',
                    severity=hou.severityType.Warning)
            else:
                print 'No filename entered for Alembic scene.'
            return False
        else :
            _abc.alembicClearArchiveCache(fileName) #清除abc 缓存
            return True
            
class ABC_Work():
    def __init__(self,abcPath,abcFile):
        self.abcFile = hou.hscriptStringExpression(abcFile)
        self.abcPath = abcPath
        self.name = [ _AbcModule.alembicGetSceneHierarchy(self.abcFile,i)[0] for i in abcPath] 
        self.houCamParmName = (
                        'aperture',
                        'aspect',
                        'focal',
                        'near',
                        'far',
                        'focus',
                        'fstop',
                        'shutter',
                        'winx',
                        'winy',
                        'winsizex',
                        'winsizey')
        for str in self.houCamParmName:
            exec("self.{}=[]".format(str))
        self.abcRange = _AbcModule.alembicTimeRange(self.abcFile)
        self.camRes = []
        self.filmaspectratio = []
        
    def getXfrom(self,cam):
        tr = []
        rot = []
        scl = []
        for t in range(int(self.abcRange[0]*hou.fps()),int(self.abcRange[1]*hou.fps())+1):
            xfrom = _AbcModule.getWorldXform(self.abcFile,cam,t/hou.fps())[0]
            xf = hou.Matrix4(xfrom)
            tr.append(xf.extractTranslates())
            rot.append(xf.extractRotates())
            scl.append(xf.extractScales())
        return tr,rot,scl
    def createCam(self):
        for cam in self.abcPath:
            camNode = hou.node('/obj').createNode('cam',self.name[self.abcPath.index(cam)])
            self.setCamView(cam)
            hasRes = self.getCamRes(cam)
            t,r,s = self.getXfrom(cam)
            self.setKey(t,camNode,'t')
            self.setKey(r,camNode,'r')
            self.setKey(s,camNode,'s')
            camNode.parmTuple('t').lock((1,1,1))
            camNode.parmTuple('r').lock((1,1,1))
            camNode.parmTuple('s').lock((1,1,1))
            for str in self.houCamParmName:
                hs = "self.setKey(self.{},camNode,'{}')".format(str,str)
                exec(hs)
            if hasRes:
                self.setKey(self.camRes,camNode,'res')
            else :
                camNode.parm('resx').set(2048)
                camNode.parm('resy').set(int(2048/self.filmaspectratio[0]))

    def setKey(self,key,node,parm):
        J = ['x','y','z','w']
        convertKey = [a for a in key]
        keyNp = np.array(convertKey)
        #print keyNp
        s  = [1,-1]
        for frame,k in enumerate(key):
            try :
                numKEY = len(k)
                #print '帧数{}，值{}'.format(frame+1 , k)
                if numKEY>1:
                    for aix,keyIndex in enumerate(k):
                        slope = np.convolve(map(lambda x:x[1],keyNp),s,mode='same') / (len(s) - 1)
                        if slope[frame]!=0:
                            keyframe = hou.Keyframe(keyIndex,hou.frameToTime(frame))
                            node.parm('{}{}'.format(parm,J[aix])).setKeyframe(keyframe)
                
            except :
                slope = np.convolve(map(lambda x:x,keyNp),s,mode='same') / (len(s) - 1)
                if slope[frame]!=0:
                    keyframe = hou.Keyframe(k,hou.frameToTime(frame))
                    node.parm('{}'.format(parm)).setKeyframe(keyframe)
            
    def setCamView(self,cam):
        
        for t in range(int(self.abcRange[0]*hou.fps()),int(self.abcRange[1]*hou.fps())+1):
            cameraDict = _abc.alembicGetCameraDict(self.abcFile,cam,t/hou.fps())
            self.filmaspectratio.append(cameraDict['filmaspectratio'])
            if cameraDict != None:
                for parmName in self.houCamParmName:
                    exec("self.{}.append({})".format(parmName,cameraDict.get(parmName)))
    def getCamRes(self,cam):
        for t in range(int(self.abcRange[0]*hou.fps()),int(self.abcRange[1]*hou.fps())+1):
            resTuple = _AbcModule.alembicGetCameraResolution(self.abcFile,cam,t)
            if resTuple != None:
                self.camRes.append(self.camRes)
                return True         
                    
                                 
                
abcFile = selFile()
abcPath = ImportABC(abcFile).getCamList()
ABC_Work(abcPath,abcFile).createCam()
