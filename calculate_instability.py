# @file calculate_instability.py
# @author Esko Kautto (esko.kautto@osumc.edu)
# @updated 2016-06-20

import os
import numpy
from copy import deepcopy
import argparse
from helpers import iteritems, tprint, timestamp


class LocusResults(object):
    def __init__(self, locus):
        self.chromosome = locus.split(':', 2)[0].strip()
        self.start = int(locus.split(':', 2)[1].split('-')[0])
        self.end = int(locus.split(':', 2)[1].split('-')[1])
        self.__k = set()
        self.__normal = {}
        self.__tumor = {}
        self.__up_to_date = False
        self.__is_normalized = False
        # end .__init__()


    """
    Returns the locus in typical chr:XXXX-YYYY format.
    """
    def locus(self):
        return '{0}:{1}-{2}'.format(
            self.chromosome, 
            self.start, 
            self.end)
        # end .locus()


    """
    Returns the value of self.__is_normalized.
    """
    def is_normalized(self):
        return self.__is_normalized
        # end .is_normalized()


    """
    Adds a row of data to the locus. Each input line is expected
    to come in with a (tab-separated) format of:
    locus    k    normal    tumor
    """
    def add(self, line):
        if self.is_normalized():
            tprint('Error: Cannot add more data once data has been normalized.')
            return False

        line = line.strip().split()
        if line[0].lower() != self.locus().lower():
            tprint('Error: Invalid locus specified ' 
                + '(expected {0}, got {1}'.format(self.locus(), line[0]))
            return False

        # Each line is expected to be in the format of:
        # locus     k   normal  tumor

        k = int(line[1])
        self.__k.add(k)
        self.__normal[k] = int(line[2])
        self.__tumor[k] = int(line[3])
        self.up_to_date = False
        return True
        # end .add()


    """
    Returns the k-values preset in both subsets, or if a 
    subset is specified, in that subset only.
    """
    def k_values(self, subset = False):
        k_values = set()
        if subset is False:
            for k in self.__k:
                if (k in self.__normal and self.__normal[k] > 0.0) or \
                    (k in self.__tumor and self.__tumor[k] > 0.0):
                    k_values.add(k)
        else:
            if subset.upper()[0] == 'N':
                # Normal data set
                subset = self.__normal
            elif subset.upper()[0] == 'T':
                # Tumor data set
                subset = self.__tumor

            for k, v in iteritems(subset):
                if v > 0.0:
                    k_values.add(k)                    

        k_values = sorted(k_values)
        return k_values
        # end .k_values()

    """
    Helper method that makes sure the entered subset identifier
    is one of the accepted ones (N or T).
    """
    @staticmethod
    def __subset_check(subset):
        subset = subset.upper()
        if subset[0] not in ['N', 'T']:
            tprint('Locus() error: Please specify (N)ormal or (T)umor as subset')
            return False
        return True
        # end .__subset_check()

    """
    Returns the total coverage/support (reads) for the locus for 
    either the normal or tumor.
    """
    def get_support(self, subset):
        if not LocusResults.__subset_check(subset):
            return False

        if subset.upper()[0] == 'N':
            return sum(self.__normal.values())
        else:
            return sum(self.__tumor.values())
        # end .get_support()


    """
    Returns the k-number and support count values for the
    specified subset. 
    """
    def get_values(self, subset, normalized = True):
        if not LocusResults.__subset_check(subset):
            return False

        if subset.upper()[0] == 'N':
            if self.is_normalized():
                data = self.__normal_normalized
            else:
                data = self.__normal
        else:
            if self.is_normalized():
                data = self.__tumor_normalized
            else:
                data = self.__tumor
        
        return deepcopy(data)
        # end .get_values()


    """
    Normalizes the data in the locus to account for coverage depth
    differences between normal and tumor samples.
    """
    def normalize(self):
        self.__normal_normalized = self.__normalized_subset('N', self.__normal)
        self.__tumor_normalized = self.__normalized_subset('T', self.__tumor)   
        self.__is_normalized = True
        # end .normalize()


    """
    Normalizes the subset of data, so that for each subset (N/T),
    the support count gets changed from a number of reads to the
    percentage of reads supporting that k-value. This addresses
    problems encountered due to varying coverage depth between
    normal and tumor samples.
    """
    def __normalized_subset(self, subset, data):
        total = self.get_support(subset)
        normalized = {}
        for k, count in iteritems(data):
            if total == 0:
                normalized[k] = 0.0
            else:
                normalized[k] = (1.0 * count) / total
        return normalized
        # end .__normalized_subset()

    # end LocusResults class definition.



class Metric(object):
    @staticmethod
    def get_k_values(locus):
        return sorted(locus.k_values())
        # end .get_k_values()

    @staticmethod 
    def get_n_values(locus):
        return locus.get_values('N')
        # end .get_n_values

    @staticmethod
    def get_t_values(locus):
        return locus.get_values('T')
        # end .get_t_values()

    @staticmethod
    def get_values(locus):
        k_values = Metric.get_k_values(locus)
        t_values = Metric.get_t_values(locus)
        n_values = Metric.get_n_values(locus)
        return tuple([k_values, t_values, n_values])
        # end .get_values()
    
    @staticmethod
    def get_list_sorted_by_key(d):
        return [d[k] for k in sorted(d.keys())]
        # end .get_list_sorted_by_key()
    
    @staticmethod
    def expand_kmer_counts(d):
        new_list = []
        for k, v in iteritems(d):
            new_list.extend([k] * v)
        return new_list
        # end .expand_kmer_counts()
    # end Metric class definition.




class EuclideanDistance(Metric):
    @staticmethod
    def get(locus):
        k_values, t_values, n_values = Metric.get_values(locus)
        distance_squared = 0
        for k in k_values:
            distance_squared += ((t_values[k] - n_values[k]) ** 2)
        return numpy.sqrt(distance_squared)
        # end EuclideanDistance.get()
    # end EuclideanDistance class definition

class CosineDissimilarity(Metric):
    @staticmethod   
    def get(locus):
        k_values, t_values, n_values = Metric.get_values(locus)

        n = []
        t = []
        for k in sorted(k_values):
            n.append(n_values[k])
            t.append(t_values[k])

        n_mag = numpy.linalg.norm(n)
        t_mag = numpy.linalg.norm(t)
        n_dot_t = numpy.dot(n, t)
        if n_mag == 0.0 or t_mag == 0.0:
            # Can't calculate data with zero-magnitude vectors
            return 0

        similarity = n_dot_t / (n_mag * t_mag)
        dist = 1 - similarity
        return dist
        # end CosineDissimilarity.get()
    # end CosineDissimilarity class definition

class Difference(Metric):
    @staticmethod
    def get(locus):
        k_values, t_values, n_values = Metric.get_values(locus)
        diff = 0.0
        for k in k_values:
            diff += abs(t_values[k] - n_values[k])
        return diff
    # end Difference class definition



def load_loci(input_filepath):
    loci = {}
    with open(input_filepath, 'r') as filein:
        n = 0
        for line in filein:
            if n is 0:
                # First line (header row), skip it
                n = 1
                continue

            line = line.strip()
            locus = line.split('\t', 2)[0].strip()

            if locus not in loci:
                loci[locus] = LocusResults(locus)
            loci[locus].add(line)
    return loci
    # end load_loci()

# Helper method for status output.
def status_call(cutoff, value):
    if value >= cutoff:
        return 'Unstable'
    else:
        return 'Stable'
    # end status_call()

# Generates output for estimated sample status based on
# cutoff values provided to the script.
def status_output(filepath, cutoffs, difference, distance, dissimilarity):
    output = []
    output.append(['{:28s}'.format('Metric'), '(Abbr)', 'Cutoff', 'Value', 'Status'])
    
    output.append([
        'Average Step-Wise Difference',
        '(DIF)',
        cutoffs['DIF'],
        round(difference, 4),
        status_call(cutoffs['DIF'], difference),
        ])

    output.append([
        'Average Euclidean Distance',
        '(EUC)',
        cutoffs['EUC'],
        round(distance, 4),
        status_call(cutoffs['EUC'], distance),
        ])

    output.append([
        'Average Cosine Dissimilarity',
        '(COS)',
        cutoffs['COS'],
        round(distance, 4),
        status_call(cutoffs['COS'], dissimilarity),
        ])

    fileout = open(filepath, 'w')
    for line in output:
        line = '\t'.join([str(x) for x in line])
        print(line)
        fileout.write(line + '\n')
    fileout.close()
    # end status_output()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input', dest='input', type=str, required=True,
        help='Input file (K-mer counts).')

    parser.add_argument('-o', '--output', dest='output', type=str, required=True,
        help='Output file.')

    parser.add_argument('--difference-cutoff', dest='dif_cutoff', type=float,
        help='Default difference cutoff value for calling a sample unstable.')

    parser.add_argument('--distance-cutoff', dest='euc_cutoff', type=float,
        help='Default distance cutoff value for calling a sample unstable.')

    parser.add_argument('--dissimilarity-cutoff', dest='cos_cutoff', type=float,
        help='Default dissimilarity cutoff value for calling a sample unstable.')


    args = parser.parse_args()

    input_filepath = os.path.abspath(args.input)
    if not os.path.isfile(input_filepath):
        tprint('Error! Input file {0} does not exist.'.format(input_filepath))
        exit(1)

    # Make sure default cutoff values have been specified.
    cutoffs = {}
    if args.dif_cutoff is None:
        tprint('Error: Default difference cutoff must be specified!')
        exit(1)
    else:
        cutoffs['DIF'] = float(args.dif_cutoff)

    if args.euc_cutoff is None:
        tprint('Error: Default distance cutoff must be specified!')
        exit(1)
    else:
        cutoffs['EUC'] = float(args.euc_cutoff)

    if args.cos_cutoff is None:
        tprint('Error: Default dissimilarity cutoff must be specified!')
        exit(1)
    else:
        cutoffs['COS'] = float(args.cos_cutoff)


    output_filepath = os.path.abspath(args.output)
    status_filepath = output_filepath + '.status'

    loci = load_loci(input_filepath)

    fileout = open(output_filepath, 'w')
    line = '\t'.join(['Locus', 'Normal_Reads', 'Tumor_Reads', 'Difference', 'Distance', 'Dissimilarity'])
    fileout.write(line + '\n')



    # Iterate through all the results to generate the output. As part of the
    # loop, count the weighted values for each metric.
    values = {'difference': [], 'distance': [] , 'dissimilarity': []}
    for l, locus in sorted(iteritems(loci)):
        # Calculate post-normalization metrics
        locus.normalize()
        difference = Difference.get(locus)
        distance = EuclideanDistance.get(locus)
        dissimilarity = CosineDissimilarity.get(locus)

        # Generate output line.
        line = '\t'.join([str(x) for x in [
            locus.locus(),
            locus.get_support('N'),
            locus.get_support('T'),
            round(difference,4),
            round(distance,4),
            round(dissimilarity, 4)]])

        # Values will be used to calculate final averaged values.
        values['difference'].append(difference)
        values['dissimilarity'].append(dissimilarity)
        values['distance'].append(distance)

        fileout.write(line + '\n')
        # end of per-locus for loop


    if len(values['difference']) > 0:
        # Generate output for final average scores.
        avg_difference = numpy.mean(values['difference'])
        avg_distance = numpy.mean(values['distance'])
        avg_dissimilarity = numpy.mean(values['dissimilarity'])
        line = '\t'.join([str(x) for x in [
            'Average',
            '-',
            '-',
            round(avg_difference,4),
            round(avg_distance,4),
            round(avg_dissimilarity, 4)]])
        fileout.write(line + '\n')
    fileout.close()

    status_output(status_filepath, cutoffs, avg_difference, avg_distance, avg_dissimilarity)
    # Done
    exit(0)
