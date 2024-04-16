def histogram(samples,name):
    plt.hist(samples)
    plt.title(name)
    plt.show()

def stats(samples):
    mean = statistics.mean(samples)
    std = statistics.stdev(samples)
    median = statistics.median(samples)
    variance = statistics.variance(samples)
    kurtosis = stats.kurtosis(samples)
    skewness = stats.skew(samples)
    print(f"mean: {mean}, std: {std}, median: {median}, variance: {variance}, kurtosis: {kurtosis}, skewness: {skewness}\n")
    return mean, std, median, variance, kurtosis, skewness


