from matplotlib import pyplot as plt
import numpy as np
from scipy import stats

def read_exper_data(fnames, distance=True):
    data = []
    ds, ws = {}, {}
    for fname in fnames:
        simfile = open(fname)
        for line in simfile.readlines():
            ln = line.split()
            data.append([round(float(ln[0]), 2), int(ln[1]), float(ln[2]),
                        int(ln[3]), float(ln[4]), int(ln[5]), float(ln[6])])
        simfile.close()
        for d in data:
            if d[0] in ds:
                ds[d[0]].append(d[1:])
            else:
                ds[d[0]] = [d[1:]]
    for d in ds:
        dds = 0
        for values in ds[d]:
            if distance:
                dds += values[1] - values[3] - values[5]
            else:
                dds += values[2] # number of conventional vehicles used for deliveries
        ws[d] = dds / len(ds[d])
    return dict(sorted(ws.items()))

def read_sample_data(fnames, distance=True):
    data = []
    ds, ws = {}, {}
    for fname in fnames:
        simfile = open(fname)
        for line in simfile.readlines():
            ln = line.split()
            data.append([round(float(ln[0]), 2), int(ln[1]), float(ln[2]),
                        int(ln[3]), float(ln[4]), int(ln[5]), float(ln[6])])
        simfile.close()
        for d in data:
            if d[0] in ds:
                ds[d[0]].append(d[1:])
            else:
                ds[d[0]] = [d[1:]]
    for d in ds:
        dds = []
        for values in ds[d]:
            if distance:
                dds.append(values[1] - values[3] - values[5]) # saved distance
            else:
                dds.append(values[2]) # number of conventional vehicles used for deliveries
        ws[d] = dds
    return dict(sorted(ws.items()))

# Statistical functions

def plot_norm(sample, bins, xlabel='Saved distance [km]', dpi=150):
    sample = np.array(sample)
    xs = np.linspace(sample.min(), sample.max(), 100)
    plt.figure(dpi=dpi)
    plt.plot(xs, stats.norm.pdf(xs, *stats.norm.fit(sample)), color='red')
    plt.hist(sample, density=True, color='royalblue', bins=bins)
    plt.xlabel(xlabel)
    plt.ylabel('Density function [-]')
    plt.show()

def sturges(n):
    return 1 + int(np.log2(n))

def sample_stats(xs, alpha=0.05):
    xs = np.array(xs)
    u_alpha = stats.norm.ppf(1 - alpha)
    mean = xs.mean()
    std = xs.std()
    var = xs.var()
    error = alpha * mean
    return {
        'min': round(xs.min(), 3),
        'max': round(xs.max(), 3),
        'mean': round(mean, 3),
        'std': round(std, 3),
        'kv': round(std / mean, 4),
        'var': round(var, 3),
        'u_alpha': round(u_alpha, 3),
        'error': round(error, 3),
        'size': round(u_alpha**2 * var / error**2, 0)
    }

def chi_square_norm(xs, alpha=0.05):
    n = len(xs)
    k = sturges(n)
    ws, bs, _ = plt.hist(xs, bins=k)
    params = stats.norm.fit(xs)
    vs = []
    for i in range(1, k + 1):
        v = n * (stats.norm.cdf(bs[i], *params) - stats.norm.cdf(bs[i - 1], *params))
        vs.append(v)
    chi2 = 0
    for i in range(k):
        chi2 += (ws[i] - vs[i])**2 / vs[i]
    df = k - len(params) - 1
    test = stats.chi2.ppf(1 - alpha, df)
    return {
        'chi2': round(chi2, 4),
        'test': round(test, 4),
        'df': df
        }

def equal_var_test(xs, ys, alpha=0.05):
    xs, ys = np.array(xs), np.array(ys)
    smaller, larger, lesser = None, None, None
    if xs.var() > ys.var():
        larger, lesser = xs, ys
        smaller = '2nd argument'
    else:
        larger, lesser = ys, xs
        smaller = '1st argument'
    var1, var2 = larger.var(), lesser.var()
    df1, df2 = len(larger) - 1, len(lesser) - 1
    Fe = var1 / var2
    Ft = stats.f.ppf(1 - alpha / 2, df1, df2)
    return {
        'smaller': smaller,
        'df1': df1,
        'df2': df2,
        'var1': var1,
        'var2': var2,
        'Fe': Fe,
        'Ft': Ft,
        'result': Fe < Ft
    }

def pooled_var_t_test(xs, ys, alpha=0.05):
    xs, ys = np.array(xs), np.array(ys)
    xmean, ymean = xs.mean(), ys.mean()
    xvar, yvar = xs.var(), ys.var()
    nx, ny = len(xs), len(ys)
    df = nx + ny - 2
    # pooled sample variance
    pvar = ((nx - 1) * xvar + (ny - 1) * yvar) / df
    t = np.abs(xmean - ymean) / np.sqrt(pvar * (1 / nx + 1 / ny))
    talpha = stats.t.ppf(1 - alpha / 2, df)
    return {
        'xmean': xmean,
        'ymean': ymean,
        'xvar': xvar,
        'yvar': yvar,
        'pvar': pvar,
        'df': df,
        't': t,
        'talpha': talpha,
        'result': t < talpha
    }

def separate_var_t_test(xs, ys, alpha=0.05):
    xs, ys = np.array(xs), np.array(ys)
    xmean, ymean = xs.mean(), ys.mean()
    xvar, yvar = xs.var(), ys.var()
    nx, ny = len(xs), len(ys)
    t = np.abs(xmean - ymean) /np.sqrt(xvar / nx + yvar / ny)
    nom = (xvar / nx + yvar / ny)**2
    denom = (xvar / nx)**2 / (nx - 1) + (yvar / ny)**2 / (ny - 1)
    df = round(nom / denom)
    talpha = stats.t.ppf(1 - alpha / 2, df)
    return {
        'xmean': xmean,
        'ymean': ymean,
        'xvar': xvar,
        'yvar': yvar,
        't': t,
        'df': df,
        'talpha': talpha,
        'result': t < talpha
    }
