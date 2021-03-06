#!/usr/bin/env python

import sys, os, glob, json, re
import pybel
import openbabel as ob

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

ff = pybel._forcefields["mmff94"]

print 'name, conf, dftE, pm7E, mmffE'

# atomization energies
atomE = [0.0] * 118
atomE[1] = -0.497859903283    #H
atomE[6] = -37.792721177046   #C
atomE[7] = -54.512803258431   #N
atomE[8] = -74.971340131182   #O
atomE[9] = -99.606601941762   #F
atomE[15] = -341.109280569995 #P
atomE[16] = -397.934238591573 #S
atomE[17] = -459.940825896724 #Cl
atomE[35] = -2573.686833420785#Br
atomE[53] = -6919.638734715522#I

for d in glob.iglob("*jobs/*"):
    # directories for both charged and neutral molecules
    name= "/".join(d.split('/')[0:2]) # name of the entry

    for f in glob.iglob(d + "/rmsd/rmsd*.mol"):
        # all the base files
        conf = f.split('/')[-1][0:-4] # conformer name/number

        # read the file (e.g., with the base bond types)
        try:
            mol = pybel.readfile("mol", f).next()
        except StopIteration:
            pm7 = d + "/rmsd/pm7/" + conf + ".mol"
            mol = pybel.readfile("mol", pm7).next()

        ff.Setup(mol.OBMol)

        # get the PM7 optimized geometry first
        orcaFile = d + "/rmsd/" + conf + "_sp.out"
        orcaSP = ""
        if os.path.isfile(orcaFile):
            with open(orcaFile) as o:
                for line in o:
                    if "FINAL SINGLE POINT ENERGY" in line:
                        orcaSP = float(line.split()[4])

        # get the MOPAC energy from the PM7 optimized
        mopacFile = d + "/rmsd/pm7/" + conf + ".out"
        mopacMM = float('nan')
        if os.path.isfile(mopacFile):
            with open(mopacFile) as m:
                for line in m:
                    if "FINAL HEAT OF FORMATION" in line:
                        mopacOpt = float(line.split()[5]) # in kcal/mol

        # save the mol file with updated coordinates
        mmffPM7 = 0.0
        try:
            mol2 = pybel.readfile("mopout", mopacFile).next()
            numAtoms = mol2.OBMol.NumAtoms()
            for i in range(numAtoms):
                oldAtom = mol.atoms[i]
                nuAtom = mol2.atoms[i]
                oldAtom.OBAtom.SetVector(nuAtom.vector)
            mol.write("sdf", "%s.mol" % (d + "/" + conf + "-pm7"), overwrite=True)
            # get the MMFF energy
            ff.SetCoordinates(mol.OBMol)
            mmffPM7 = ff.Energy() # in kcal/mol
        except:
            i = 1

        # now look for the MMFF-optimized geometry (e.g., DFT single-point)
        orcaMM = ""
        orcaFile = d + "/rmsd/" + conf + "-mmff_sp.out"
        if os.path.isfile(orcaFile):
            with open(orcaFile) as o:
                for line in o:
                    if "FINAL SINGLE POINT ENERGY" in line:
                        orcaMM = float(line.split()[4])
        mopacFile = d + "/rmsd/pm7/" + conf + "-mmff-opt.out"
        mopacMM = float('nan')
        if os.path.isfile(mopacFile):
            with open(mopacFile) as m:
                for line in m:
                    if "FINAL HEAT OF FORMATION" in line:
                        mopacMM = float(line.split()[5]) # in kcal/mol
        mmffOpt = 0.0
        try:
            mol2 = pybel.readfile("mopout", mopacFile).next()
            numAtoms = mol2.OBMol.NumAtoms()
            for i in range(numAtoms):
                oldAtom = mol.atoms[i]
                nuAtom = mol2.atoms[i]
                oldAtom.OBAtom.SetVector(nuAtom.vector)
            mol.write("sdf", "%s.mol" % (d + "/" + conf + "-mmff"), overwrite=True)
            # get the MMFF energy
            ff.SetCoordinates(mol.OBMol)
            mmffOpt = ff.Energy() # in kcal/mol
        except:
            i = 2

        ####
        # Now the DFT optimized geometry
        ####
        orcaFile = d + "/rmsd/" + conf + "_opt.out"
        orcaOpt = ""
        if os.path.isfile(orcaFile):
            with open(orcaFile) as o:
                for line in o:
                    if "FINAL SINGLE POINT ENERGY" in line:
                        orcaOpt = float(line.split()[4])

        mopacFile = d + "/rmsd/" + conf + "_opt_pm7.out"
        mopacSP = float('nan')
        if os.path.isfile(mopacFile):
            with open(mopacFile) as m:
                for line in m:
                    if "FINAL HEAT OF FORMATION" in line:
                        mopacSP = float(line.split()[5]) # in kcal/mol

        # get the MMFF energy for this
        mmffDFT = 0.0
        try:
            mol2 = pybel.readfile("mopout", mopacFile).next()
            numAtoms = mol2.OBMol.NumAtoms()
            for i in range(numAtoms):
                oldAtom = mol.atoms[i]
                nuAtom = mol2.atoms[i]
                oldAtom.OBAtom.SetVector(nuAtom.vector)
            mol.write("sdf", "%s.mol" % (d + "/" + conf + "-opt"), overwrite=True)
            ff.SetCoordinates(mol.OBMol)
            mmffDFT = ff.Energy() # in kcal/mol
        except:
            i = 3

        # convert the orcaSP and orcaOpt energies
        # to atomization energies in kcal/mol
        if is_number(orcaSP) or is_number(orcaOpt) or is_number(orcaMM):
            elements = [0] * 118
            try:
                for atom in mol.atoms: # how many of each element are there?
                    elements[atom.atomicnum] = elements[atom.atomicnum] + 1
                totalAtomE = 0.0 # get the atomic contributions
                for e in range(len(elements)):
                    totalAtomE = totalAtomE + elements[e] * atomE[e]
                if is_number(orcaSP):
                    orcaSP = (totalAtomE - float(orcaSP)) * 627.509469 # hartree to kcal/mol
                if is_number(orcaOpt):
                    orcaOpt = (totalAtomE - float(orcaOpt)) * 627.509469 # hartree to kcal/mol
                if is_number(orcaMM):
                    orcaMM = (totalAtomE - float(orcaMM)) * 627.509469 # hartree to kcal/mol
            except AttributeError:
                print "%s, %s, error" % (name, conf)
                continue

        conf = conf.rstrip()
#        try:
#            print "%s, %s, %f, %f, %f, %f, %f, %f" % (name, conf, orcaSP, mopacOpt, mmffPM7, orcaOpt, mopacSP, mmffDFT)
#        except TypeError:
#            print "%s, %s, error" % (name, conf)
        if is_number(orcaMM):
            print "%s, %s-mmff, %f, %f, %f" % (name, conf, orcaMM, mopacMM, mmffOpt)
        else:
            try:
                print "%s, %s-mmff, nan, %f, %f" % (name, conf, mopacMM, mmffOpt)
            except:
                print "%s, %s-mmff" % (name, conf), type(mopacMM), type(mmffOpt)
        try:
            print "%s, %s-pm7, %f, %f, %f" % (name, conf, orcaSP, mopacOpt, mmffPM7)
        except:
            pass
        try:
            print "%s, %s-opt, %f, %f, %f" % (name, conf, orcaOpt, mopacSP, mmffDFT)
        except TypeError:
            print "%s, %s-opt, error" % (name, conf), type(orcaOpt), type(mopacSP), type(mmffDFT)
