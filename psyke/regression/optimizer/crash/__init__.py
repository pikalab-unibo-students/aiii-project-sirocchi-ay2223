from enum import Enum

import numpy as np
import pandas as pd

from psyke import Extractor
from psyke.regression.optimizer import Objective, Optimizer


class CRASH(Optimizer):
    class Algorithm(Enum):
        CReEPy = 1,
        CREAM = 2

    def __init__(self, predictor, dataframe: pd.DataFrame, max_mae_increase: float = 1.2,
                 min_rule_decrease: float = 0.9, readability_tradeoff: float = 0.1, max_depth: int = 10,
                 patience: int = 5, algorithm: Algorithm = Algorithm.CREAM, objective: Objective = Objective.MODEL):
        super().__init__(readability_tradeoff, algorithm)
        self.predictor = predictor
        self.dataframe = dataframe
        self.max_mae_increase = max_mae_increase
        self.min_rule_decrease = min_rule_decrease
        self.patience = patience
        self.max_depth = max_depth
        self.objective = objective
        self.model_mae = abs(self.predictor.predict(dataframe.iloc[:, :-1]).flatten() -
                             dataframe.iloc[:, -1].values).mean()

    def search(self):
        self.params = self.__search_depth()

    def __search_depth(self):
        params = []
        best = None

        for depth in range(1, self.max_depth + 1):
            p = self.__search_threshold(depth)
            b = Optimizer._best(p)[1]
            print()
            improvement = self._depth_improvement(
                [best[0], best[1]], [b[0], b[1]]
            ) if best is not None else np.inf

            best = b
            params += p

            if len(params) > 1 and improvement < 1.2:
                break
        return params

    def __search_threshold(self, depth):
        step = self.model_mae / 2.0
        threshold = self.model_mae * 0.9
        params = []
        patience = self.patience
        while patience > 0:
            print(f"{self.algorithm}. Depth: {depth}. Threshold = {threshold:.2f}. ", end="")
            extractor = Extractor.creepy(self.predictor, depth, threshold, 10, False) \
                if self.algorithm == CRASH.Algorithm.CReEPy \
                else Extractor.cream(self.predictor, depth, threshold, 10, False)
            _ = extractor.extract(self.dataframe)
            mae, n = extractor.mae(self.dataframe), extractor.n_rules
            print(f"MAE = {mae:.2f}, {n} rules")

            if len(params) == 0:
                params.append((mae, n, depth, threshold))
                threshold += step
                continue

            if n == 1:
                params.append((mae, n, depth, threshold))
                break

            if mae > params[0][0] * self.max_mae_increase:
                break

            improvement = (params[-1][0] / mae) + (1 - n / params[-1][1])

            if improvement <= 1 or n > np.ceil(params[-1][1] * self.min_rule_decrease):
                patience -= 1
                step = max(step, abs(mae - threshold) / max(patience, 1))
            if mae != params[-1][0] or n != params[-1][1]:
                params.append((mae, n, depth, threshold))
            threshold += step
        return params

    def _print_params(self, name, params):
        print("**********************")
        print(f"*Best {name}*")
        print("**********************")
        print(f"MAE = {params[0]:.2f}, {params[1]} rules")
        print(f"Threshold = {params[3]:.2f}")
        print(f"Depth = {params[2]}")
