import numpy as np
from LoadData import *
import numpy.matlib

class GetInst_A(object):
    def __init__(self, useful_sp_lab, img3d, gt, trpos):
        self.useful_sp_lab = [x[0] for x in useful_sp_lab]
        self.scale=len(self.useful_sp_lab)
        self.ReduceZeros(gt)
        self.img3d = img3d
        [self.r, self.c, self.l] = np.shape(img3d)
        self.num_classes = int(np.max(gt))
        self.img2d = np.reshape(img3d,[self.r*self.c, self.l])
        self.sp_num = np.array([ np.max(x) for x in self.useful_sp_lab], dtype='int')
        gt = np.array(gt, dtype='int')
        self.gt1d = np.reshape(gt, [self.r*self.c])
        self.gt_tr = np.array(np.zeros([self.r*self.c]), dtype='int')
        self.gt_te = self.gt1d
        trpos = np.array(trpos, dtype='int')
        self.trpos = (trpos[:,0]-1)*self.c+trpos[:,1]-1
        ###
        self.sp_mean = [np.zeros([x, self.l]) for x in self.sp_num]
        self.sp_center_px = [np.zeros([x, self.l])  for x in self.sp_num]
        self.sp_label = [np.zeros([x])  for x in self.sp_num]
        self.trmask = [np.zeros([x])  for x in self.sp_num]
        self.temask = [np.ones([x])  for x in self.sp_num]
        self.sp_nei = []
        self.sp_label_vec = []
        self.sp_A = [] 
        self.support = []
        self.CalSpMean()    
        self.CalSpNei()
        self.CalSpA()

    
    def ReduceZeros(self,gt):
        for i in range(len(self.useful_sp_lab)):
            sp_lab=self.useful_sp_lab[i]
            n=0
            for sp_idx in range(1,sp_lab.max()+1):
                sp_pos=np.argwhere(sp_lab==sp_idx)
                if gt[sp_pos[:,0],sp_pos[:,1]].sum()==0:
                    sp_lab[sp_pos[:,0],sp_pos[:,1]]=0
                else:
                    n+=1
                    sp_lab[sp_pos[:,0],sp_pos[:,1]]=n
            self.useful_sp_lab[i]=sp_lab
            print('Final number of superpixels is',n,'for',i,'of',len(self.useful_sp_lab))
    
    def CalSpMean(self):
        for scale_idx in range(self.scale):
            self.gt_tr[self.trpos] = self.gt1d[self.trpos]
            mark_mat = np.zeros([self.r*self.c])
            mark_mat[self.trpos] = -1
            for sp_idx in range(1, self.sp_num[scale_idx]+1): #calculate the sp_mean and sp_label of each super-pixel one-by-one
                region_pos_2d = np.argwhere(self.useful_sp_lab[scale_idx] == sp_idx)
                region_pos_1d = region_pos_2d[:, 0]*self.c + region_pos_2d[:, 1]
                px_num = np.shape(region_pos_2d)[0] #px_num = pixel number in the superpixel
                if np.sum(mark_mat[region_pos_1d])<0:#the train_loc in mark_mat is -1
                    self.trmask[scale_idx][sp_idx-1] = 1
                    self.temask[scale_idx][sp_idx-1] = 0
                region_fea = self.img2d[region_pos_1d, :]
                if self.trmask[scale_idx][sp_idx-1] == 1:
                    region_labels = self.gt_tr[region_pos_1d]
                else:
                    region_labels = self.gt_te[region_pos_1d] # Can you use the gt to calculate the region_labels here?
                ####
                if len(np.delete(np.bincount(region_labels), 0))==0:
                    print(sp_idx)
                ####
                self.sp_label[scale_idx][sp_idx-1] = np.argmax(np.delete(np.bincount(region_labels), 0))+1 # sp_label is determined by the region labels(the most labels index) 
                region_pos_idx = np.argwhere(region_labels == self.sp_label[scale_idx][sp_idx-1])
                pos1 = region_pos_1d[region_pos_idx]
                sp_rps = np.mean(self.img2d[pos1, :], axis = 0) # average of the training pixels in the superpixel
                vj = np.sum(np.power(np.matlib.repmat(sp_rps, px_num, 1)-region_fea, 2), axis=1)
                vj= np.exp(-1*vj) # coefficient of the pixels(region_fea)
                self.sp_mean[scale_idx][sp_idx-1, :] = np.sum(np.reshape(vj, [np.size(vj), 1])*region_fea, axis=0)/np.sum(vj)# weighted average
            sp_label_mat = np.zeros([self.sp_num[scale_idx], self.num_classes]) # one-hot coding
            for row_idx in range(np.shape(self.sp_label[scale_idx])[0]):
                col_idx = int(self.sp_label[scale_idx][row_idx])-1
                sp_label_mat[row_idx, col_idx] = 1
            self.sp_label_vec.append(self.sp_label[scale_idx])
            self.sp_label[scale_idx] = sp_label_mat
            
    def CalSpNei(self): #find the adjacent superpixels of each super-pixel one-by-one
        for scale_idx in range(self.scale):
            sp_nei=[]
            for sp_idx in range(1, self.sp_num[scale_idx]+1):
                nei_list = []
                region_pos_2d = np.argwhere(self.useful_sp_lab[scale_idx] == sp_idx)
                r1 = np.min(region_pos_2d[:, 0])
                r2 = np.max(region_pos_2d[:, 0])
                c1 = np.min(region_pos_2d[:, 1])
                c2 = np.max(region_pos_2d[:, 1])
                for r in range(r1, r2+1):#按行遍历，找到最临近的useful_spp_lab
                    pos1 = np.argwhere(region_pos_2d[:, 0] == r)[:, 0]
                    try:
                        min_col = np.min(region_pos_2d[:, 1][pos1])
                        max_col = np.max(region_pos_2d[:, 1][pos1])
                    except:
                        pass #print(region_pos_2d[:, 1][pos1])
                    nc1 = min_col-1
                    nc2 = max_col+1
                    if nc1>=0:
                        nei_list.append(self.useful_sp_lab[scale_idx][r, nc1])
                    if nc2<=self.c-1:
                        nei_list.append(self.useful_sp_lab[scale_idx][r, nc2])
                for c in range(c1, c2+1):#按列遍历，找到最临近的useful_spp_lab
                    pos1 = np.argwhere(region_pos_2d[:, 1] == c)[:, 0]
                    try:
                        min_row = np.min(region_pos_2d[:, 0][pos1])
                        max_row = np.max(region_pos_2d[:, 0][pos1])  
                    except:
                        pass #print(region_pos_2d[:, 0][pos1])
                    nr1 = min_row-1
                    nr2 = max_row+1
                    if nr1>=0:
                        nei_list.append(self.useful_sp_lab[scale_idx][nr1, c])
                    if nr2<=self.r-1:
                        nei_list.append(self.useful_sp_lab[scale_idx][nr2, c])
                nei_list = list(set(nei_list))
                nei_list = [int(list_item) for list_item in nei_list]
                if 0 in nei_list:
                    nei_list.remove(0)
                sp_nei.append(nei_list if len(nei_list) else [])
            self.sp_nei.append(sp_nei)
        
    def CalSpA(self):
        for scale_idx in range(self.scale):
            sp_A_s1 = np.zeros([self.sp_num[scale_idx], self.sp_num[scale_idx]])
            for sp_idx in range(1, self.sp_num[scale_idx]+1):
                sp_idx0 = sp_idx-1 
                cen_sp = self.sp_mean[scale_idx][sp_idx0]
                nei_idx = self.sp_nei[scale_idx][sp_idx0] # list
                nei_idx0 = np.array([list_item-1 for list_item in nei_idx], dtype=int)
                cen_nei = self.sp_mean[scale_idx][nei_idx0, :]
                dist1 = self.Eu_dist(cen_sp, cen_nei)
                sp_A_s1[sp_idx0, nei_idx0] = dist1
                
            self.sp_A.append(sp_A_s1)
            self.sp_A[-1] = self.SymmetrizationMat(self.sp_A[-1])
            

    def AddConnection(self, A):
        A1 = A.copy()
        num_rows = np.shape(A)[0]
        for row_idx in range(num_rows): #two-hops extension the check the rows one-by-one 
            pos1 = np.argwhere(A[row_idx, :]!=0) 
            for num_nei1 in range(np.size(pos1)):
                nei_ori = A[pos1[num_nei1, 0], :].copy() 
                pos2 = np.argwhere(nei_ori!=0)[:, 0] 
                nei1 = self.sp_mean[pos2, :]
                dist1 = self.Eu_dist(self.sp_mean[row_idx, :], nei1)
                A1[row_idx, pos2] = dist1
            A1[row_idx, row_idx] = 0 #set 0 to the diag
        return A1
             
    def Eu_dist(self, vec, mat):
        rows = np.shape(mat)[0]
        mat1 = np.matlib.repmat(vec, rows, 1)
        dist1 = np.exp(-0.1*np.sum(np.power(mat1-mat, 2), axis = 1))
        return dist1
    
    def SymmetrizationMat(self, mat):
        [r, c] = np.shape(mat)
        if r!=c:
            print('Input is not square matrix')
            return
        for rows in range(r):
            for cols in range(rows, c):
                e1 = mat[rows, cols]
                e2 = mat[cols, rows]
                if e1+e2!=0 and e1*e2 == 0:
                    mat[rows, cols] = e1+e2
                    mat[cols, rows] = e1+e2
        return mat
    def CalSupport(self, A):
        num1 = np.shape(A)[0]
        A_ = A + 1*np.eye(num1)
        D_ = np.sum(A_, 1)
        D_05 = np.diag(D_**(-0.5))
        support = np.matmul(np.matmul(D_05, A_), D_05)
        return support #(D_**(-0.5)A(D_**(-0.5))Z
