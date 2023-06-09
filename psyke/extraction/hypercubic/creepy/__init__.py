from __future__ import annotations

from abc import ABC
from collections import Iterable
import numpy as np
import pandas as pd
from sklearn.base import ClassifierMixin
from tuprolog.core import clause
from tuprolog.theory import Theory
from psyke import Clustering
from psyke.clustering import HyperCubeClustering
from psyke.extraction.hypercubic import HyperCubeExtractor
from psyke.utils import Target


class CReEPy(HyperCubeExtractor, ABC):
    """
    Explanator implementing CReEPy algorithm.
    """

    def __init__(self, predictor, depth: int, error_threshold: float, output: Target = Target.CONSTANT,
                 gauss_components: int = 5, ranks: list[(str, float)] = [], ignore_threshold: float = 0.0,
                 normalization=None, clustering=Clustering.exact):
        super().__init__(predictor, Target.CLASSIFICATION if isinstance(predictor, ClassifierMixin) else output,
                         normalization)
        self.clustering = clustering(depth, error_threshold, self._output, gauss_components)
        self.ranks = ranks
        self.ignore_threshold = ignore_threshold

    def _extract(self, dataframe: pd.DataFrame, mapping: dict[str: int] = None, sort: bool = True) -> Theory:
        if not isinstance(self.clustering, HyperCubeClustering):
            raise TypeError("clustering must be a HyperCubeClustering")

        self.clustering.fit(dataframe)
        self._hypercubes = self.clustering.get_hypercubes()
        for cube in self._hypercubes:
            for dimension in self._ignore_dimensions():
                cube[dimension] = [-np.inf, np.inf]
        theory = self._create_theory(dataframe)
        last_clause = list(theory.clauses)[-1]
        theory.retract(last_clause)
        theory.assertZ(clause(
            last_clause.head, [list(last_clause.body)[-1]] if self._output is Target.REGRESSION else []))
        last_cube = self._hypercubes[-1]
        for dimension in last_cube.dimensions.keys():
            last_cube[dimension] = [-np.inf, np.inf]
        return theory

    def _ignore_dimensions(self) -> Iterable[str]:
        return [dimension for dimension, relevance in self.ranks if relevance < self.ignore_threshold]
