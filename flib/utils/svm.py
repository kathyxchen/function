import argparse

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from multiprocessing import Pool

from flib.core.dab import Dab
from flib.core.gmt import GMT
from flib.core.omim import OMIM
from flib.core.onto import DiseaseOntology
from flib.core.labels import OntoLabels, Labels
from flib.core.svm import NetworkSVM

parser = argparse.ArgumentParser(description='Generate a file of updated disease gene annotations')
parser.add_argument('--input', '-i', dest='input', type=str,
                                help='Input dab file')
parser.add_argument('--output', '-o', dest='output', type=str,
                                help='Output directory')
parser.add_argument('--gmt', '-g', dest='gmt', type=str,
                                help='Input GMT (geneset) file')
parser.add_argument('--dir', '-d', dest='dir', type=str,
                                help='Directory of labels')
parser.add_argument('--all', '-a', dest='predict_all', action='store_true',
                                default=False,
                                help='Predict all genes')
parser.add_argument('--threads', '-t', dest='threads', type=int,
                                default=12,
                                help='Number of threads')
parser.add_argument('--best-params', '-b', dest='best_params', action='store_true',
                                default=False,
                                help='Select best parameters by cross validation')
args = parser.parse_args()

MIN_POS, MAX_POS = 5, 500

if args.gmt:
    # Load GMT genes onto Disease Ontology and propagate
    do = DiseaseOntology.generate()
    gmt = GMT(filename=args.gmt)
    for (gsid, genes) in gmt.genesets.iteritems():
        term = do.get_term(gsid)
        for gid in genes:
            term.add_annotation(gid)

    do.propagate()

    # Filter terms by number of gene annotations
    terms = [term.go_id for term in do.get_termobject_list() \
        if len(term.annotations) >= MIN_POS and len(term.annotations) <= MAX_POS]

    # Build ontology aware labels
    lines = open('../../files/do_slim.txt').readlines()
    slim_terms = set([l.strip() for l in lines])
    labels = OntoLabels(obo=do, slim_terms=slim_terms)
elif args.dir:
    labels = Labels(labels_dir=args.dir)
    terms = [term for term in labels.get_terms() \
                if len(labels.get_labels(term)[0]) >= MIN_POS and
                len(labels.get_labels(term)[0]) <= MAX_POS]
else:
    OMIM().load_onto(onto=do)
    do.propagate()

dab = Dab(args.input)
svm = NetworkSVM(dab)

def run_svm(term):
    (pos, neg) = labels.get_labels(term)

    logger.info('Running SVM for %s, %i pos, %i neg', term, len(pos), len(neg))

    predictions = svm.predict(pos, neg,
            predict_all = args.predict_all,
            best_params = args.best_params)
    svm.print_predictions(args.output + '/' + term, pos, neg)

pool = Pool(args.threads)
pool.map(run_svm, terms)
pool.close()