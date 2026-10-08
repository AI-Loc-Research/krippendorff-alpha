import numpy as np
import krippendorff


def alpha_nominal(matrix: np.ndarray) -> float:
    values = matrix[~np.isnan(matrix)]

    if np.unique(values).size < 2:
        return float("nan")

    return float(
        krippendorff.alpha(
            reliability_data=matrix,
            level_of_measurement="nominal",
        )
    )


# Official fast-krippendorff example
reliability_data = np.array([
    [np.nan, np.nan, np.nan, np.nan, np.nan, 3, 4, 1, 2, 1, 1, 3, 3, np.nan, 3],
    [1,      np.nan, 2,      1,      3,      3, 4, 3, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
    [np.nan, np.nan, 2,      1,      3,      4, 4, np.nan, 2, 1, 1, 3, 3, np.nan, 4],
], dtype=float)

result = alpha_nominal(reliability_data)

print("Our function:", result)
print("Expected:    ", 0.691358)
print("Difference:  ", abs(result - 0.691358))