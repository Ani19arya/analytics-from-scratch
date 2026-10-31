"""Lesson 07 solution: sampling and the central limit theorem, by hand."""
import csv
import math
import random


def mean(values):
    values = list(values)
    if not values:
        raise ValueError("mean of an empty list")
    return sum(values) / len(values)


def population_sd(values):
    """SD of a complete population: divide the squared deviations by N."""
    values = list(values)
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def sample_sd(values):
    """SD estimated from a sample: divide by n - 1."""
    values = list(values)
    if len(values) < 2:
        raise ValueError("a sample SD needs at least 2 values")
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def standard_error(values):
    """Estimated standard error of the mean of this sample: sample SD / sqrt(n)."""
    values = list(values)
    return sample_sd(values) / math.sqrt(len(values))


def sample_means(population, n, draws, seed):
    """Draw `draws` random samples of n values (with replacement) and return their means."""
    if n < 1 or draws < 0:
        raise ValueError("n must be at least 1 and draws 0 or more")
    population = list(population)
    if not population:
        raise ValueError("empty population")
    rng = random.Random(seed)
    return [sum(rng.choices(population, k=n)) / n for _ in range(draws)]


def share_within(values, centre, half_width):
    values = list(values)
    if not values:
        raise ValueError("no values")
    return sum(1 for v in values if centre - half_width <= v <= centre + half_width) / len(values)


def read_orders(path):
    with open(path, newline="") as f:
        return [float(row["order_value"]) for row in csv.DictReader(f)]


def read_weeks(path):
    weeks = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            weeks.setdefault(row["week_start"], []).append(float(row["order_value"]))
    return weeks


def summarise(population_path, weeks_path, n=18, draws=10000, seed=1):
    pop = read_orders(population_path)
    mu, sigma = mean(pop), population_sd(pop)
    true_se = sigma / math.sqrt(n)
    means = sample_means(pop, n, draws, seed)
    weeks = read_weeks(weeks_path)
    first, second = sorted(weeks)
    se1, se2 = standard_error(weeks[first]), standard_error(weeks[second])
    return {
        "pop_mean": mu, "pop_sd": sigma, "true_se": true_se,
        "mean_of_means": mean(means), "sd_of_means": sample_sd(means),
        "share_within_1_96": share_within(means, mu, 1.96 * true_se),
        "week1_mean": mean(weeks[first]), "week1_se": se1,
        "week2_mean": mean(weeks[second]), "week2_se": se2,
        "change": mean(weeks[second]) - mean(weeks[first]),
        "change_se": math.sqrt(se1 ** 2 + se2 ** 2),
    }


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "..", "data")
    result = summarise(os.path.join(data, "population.csv"), os.path.join(data, "weeks.csv"))
    for key, value in result.items():
        print(key, round(value, 4) if key == "share_within_1_96" else round(value, 2))
