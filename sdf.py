#-------------------------------------------------------------------------------
# Name:        sdf
# Purpose:     operations with sdf files (reading)
#
# Author:      Pavel Polishchuk
#
# Created:     11.01.2013
# Copyright:   (c) Pavel Polishchuk 2013
# Licence:     GPLv3
#-------------------------------------------------------------------------------


from mols import Mol3 as Mol
from files import ReadPropertyRange, RangedLetter


formal_charges_table = {'0': 0,
                        '1': 3,
                        '2': 2,
                        '3': 1,
                        '4': 0,
                        '5': -1,
                        '6': -2,
                        '7': -3}


def ReadSDF(fname, opt_diff, fsetup, parse_stereo):
    """
    INPUT: sdf-filename
    OUTPUT: dict of molecules, where key is the title of the moleculae taken from the first line of mol-record
    """

    def MolstrToMol(molstr, opt_diff, parse_stereo):

        mol = Mol()
        mol.stereo = parse_stereo
        mol.title = molstr[0]
        natoms = int(molstr[3][0:3])
        nbonds = int(molstr[3][3:6])

        # read atoms
        id = 0
        for line in molstr[4:4 + natoms]:
            x = float(line[0:10])
            y = float(line[10:20])
            z = float(line[20:30])
            label = line[30:33].strip()
            formal_charge = line[36:39].strip()
            id += 1
            mol.AddAtom(id, label, x, y, z, formal_charges_table.get(formal_charge, 0))

        # read bonds
        for line in molstr[4 + natoms:4 + natoms + nbonds]:
            id1 = int(line[0:3])
            id2 = int(line[3:6])
            bond_type = int(line[6:9])
            mol.AddBond(id1, id2, bond_type)

        start_line_property_block = 4 + natoms + nbonds

        # read properties from sdf fields
        if opt_diff:
            # prepare data field; missing values in data string is replaced by 9999
            opt_diff = [el.lower() for el in opt_diff]
            data_dict = dict()
            i = start_line_property_block
            while i < len(molstr) - 1:
                if molstr[i][:3] == '> <' or molstr[i][:4] == '>  <':
                    line = molstr[i].strip()[4:-1].lower()
                    if line in opt_diff:
                        i += 1
                        s = molstr[i].strip().split(";")
                        try:
                            data_dict[line] = [float(el.replace(",", ".")) if el != "" else None for el in s]
                        except ValueError:
                            data_dict[line] = [el if el != "" else None for el in s]
                i += 1
            # add labels
            for prop_name in data_dict.keys():
                prop_range = ReadPropertyRange(fsetup, prop_name)
                for i, a in enumerate(sorted(mol.atoms.keys())):
                    # if value is numeric use ranges, if value is string use it as label itself
                    label = data_dict[prop_name][i] if type(data_dict[prop_name][i]) is str else RangedLetter(data_dict[prop_name][i], prop_range)
                    mol.atoms[a]['property'][prop_name] = {'value': data_dict[prop_name][i],
                                                           'label': label}

        # parse stereo
        if parse_stereo:

            i = start_line_property_block

            while i < len(molstr) - 1:
                if molstr[i][:3] == '> <' or molstr[i][:4] == '>  <':
                    line = molstr[i].strip()[4:-1].lower()
                    # read stereo analysis data
                    if line == 'stereoanalysis':
                        i += 1
                        while molstr[i].strip() and molstr[i][0] != '>':
                            tmp = molstr[i].strip().split(' ')
                            if tmp[0] == 'CISTRANS':
                                # atoms enumeration in Chemaxon output starts from 0
                                id1 = int(tmp[1][1:-1]) + 1
                                id2 = int(tmp[2][:-1]) + 1
                                bond_stereo = tmp[-1].lower()
                                if bond_stereo == 'wiggly':
                                    bond_stereo = 0
                                elif bond_stereo == 'e':
                                    bond_stereo = 2
                                elif bond_stereo == 'z':
                                    bond_stereo = 1
                                mol.SetDoubleBondConfig(id1, id2, bond_stereo)
                            i += 1
                        break
                i += 1

            mol.SetCyclicDoubleBondsCis()

        return mol

    mols = {}
    molstr = []
    f = open(fname)
    for line in f:
        if line.find("$$$$") < 0:
            molstr.append(line.rstrip())
        else:
            m = MolstrToMol(molstr, opt_diff, parse_stereo)
            mols[m.title] = m
            molstr = []
    return mols
