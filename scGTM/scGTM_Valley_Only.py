import pandas as pd
import json
import numpy as np
import pyswarms as ps
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from scipy.optimize import fsolve
from scipy.stats import nbinom, poisson, norm
from pseudotimeAPI_valley import *
from pseudotimeEstInfer_valley import *
import csv

import warnings
warnings.filterwarnings("ignore")

def main(gene_index = 100, t=None, y1=None, gene_name=None, marginal="ZIP", iter_num=50, data_dir=None, save_dir=None, plot_args=None):

    #print("Loading data......")

    ## LOAD DATA
    #data = pd.read_csv(data_dir)
    #print("Loading finished!")

    ## TAKE NEEDED DATA
    #t = data.iloc[:, 1]
    #y1 = np.floor(data.iloc[:, gene_index])
    #gene_name = data.columns[gene_index]

    ## Flag calculation
    #flag = (np.corrcoef(t[t<0.5], y1[t<0.5])[0, 1]) < 0 and (np.corrcoef(t[t>0.5], y1[t>0.5])[0, 1]) > 0
    #flag = False
    #print("The need of transformation: " + str(flag))

    flag = True
    
    #if flag:
    #    raw = np.copy(y1)
    #y1 = np.log(y1 + 1)
    b = np.log(np.max(y1)+1)
    #    y1 = -y1 + np.max(y1)
    #    y1 = np.floor(np.exp(y1)-1)
    #else:
    #    pass

    ## ESTIMATION
    print("\nWe are estimating gene %d with marginal %s." % (gene_index, marginal))

    result = {}
    gcost, gbest = estimation(y1, t, marginal, iter_num)
    result['negative_log_likelihood'] = gcost

    if gcost > 1e2:
        print("\nBest negative log-likelihood: ", np.round(gcost, 2), "\n")
    else:
        print("\nAlgorithm fails to find reasonable estimation.\n")

    if marginal == "ZIP":
        result['mu'] = gbest[0]; result['k1'] = gbest[1]
        result['k2'] = gbest[2]; result['t0'] = gbest[3]; result['phi'] = "Nah"; result['b'] = b
        result['alpha'] = gbest[4]; result['beta'] = gbest[5]
        #result['AIC'] = 2*gcost + 2*6

        print("Best parameter estimation:\n",
              "mu , k1 , k2 , t0 , p:\n",
              np.round(gbest, 2), "\n")
    elif marginal == "ZINB":
        gbest[4] = np.maximum(np.floor(gbest[-2]), 1)
        result['mu'] = gbest[0]; result['k1'] = gbest[1]; result['k2'] = gbest[2]
        result['t0'] = gbest[3]; result['phi'] = gbest[4]; result['alpha'] = gbest[5]; result['beta'] = gbest[6]; result['b'] = b 
        #result['AIC'] = 2*gcost + 2*7
        print("Best parameter estimation:\n",
              "mu , k1 , k2 , t0 , phi , p:\n",
              np.round(gbest, 2), "\n")
    elif marginal == "Poisson":
        result['mu'] = gbest[0]
        result['k1'] = gbest[1]
        result['k2'] = gbest[2]
        result['t0'] = gbest[3]
        result['phi'] = "Nah"; result['b'] = b
        result['p'] = "Nah"
        #result['AIC'] = 2*gcost + 2*5
        print("Best parameter estimation:\n",
              "mu , k1 , k2 , t0:\n",
              np.round(gbest[:-1], 2), "\n")
    else:
        gbest[-2] = np.maximum(np.floor(gbest[-2]), 1)
        result['mu'] = gbest[0]
        result['k1'] = gbest[1]
        result['k2'] = gbest[2]
        result['t0'] = gbest[3]
        result['phi'] = gbest[4]; result['b'] = b
        result['p'] = "Nah"
        #result['AIC'] = 2*gcost + 2*6
        print("Best parameter estimation:\n",
              "mu , k1 , k2 , t0 , phi:\n",
              np.round(gbest[:-1], 2), "\n")

    ## PLOTTING
    if plot_args is not None:
        color = plot_args['color']
        cmap = plot_args['cmap']
    else:
        color = ['red', 'blue', 'orange', 'darkgreen']
        cmap = 'PRGn'

    fig, ax = plt.subplots(figsize=(10, 8))
    #if flag:
    #    y1 = raw
    log_data = np.log(y1 + 1)
    plt.scatter(t, log_data, s=10, c=log_data, cmap=plt.get_cmap(cmap))
    plt.ylim(np.min(log_data) - 1, np.max(log_data) + 1)

    plot_result(gbest, t, color, marginal=marginal, flag=flag, y1=y1)

    #trend = {"True": "Valley", "False": "Hill"}
    trend = {"True": "Valley-shaped", "False": "Hill-shaped"}
    #plt.title("Gene: " + str(gene_name) + "; Distribution: " + marginal + ';' + " Trend: " + trend[str(flag)], fontsize=25)
    plt.title("Gene: " + str(gene_name) + "\n" + trend[str(flag)] + " scGTM w/ " + marginal, fontsize=24)

    plt.text(result['t0']+0.03, -0.75, r"$t_0$", fontsize=24, color=color[2])
    #plt.show()

    plt.savefig(save_dir + str(gene_index-1) + marginal + ".png")

    ## FISHER INFORMATION
    fisher, var, t0_lower, t0_upper = inference(t, gbest, marginal)
    result['t0_lower'] = t0_lower
    result['t0_upper'] = t0_upper

    #print("Inverse Fisher information matrix of first 4 parameters or t0 alone:\n",
    #      var , "\n")

    ## CONFIDENCE INTERVAL
    print("The 95% confidence interval of the activation time t0:\n" +
          "t0 : (" + str(t0_lower) + ", " + str(t0_upper) + ")")

    result['k1_lower'] = result['k1_upper'] = result['k2_lower'] = \
        result['k2_upper'] = result['mu_lower'] = result['mu_upper'] =  "Nah"

    if np.ndim(var) > 1:
        result['t0_std'] = np.sqrt(var[0, 0])
        k1_lower = np.round(gbest[1] - 1.96 * np.sqrt(var[1, 1]), 3)
        k1_upper = np.round(gbest[1] + 1.96 * np.sqrt(var[1, 1]), 3)
        k2_lower = np.round(gbest[2] - 1.96 * np.sqrt(var[2, 2]), 3)
        k2_upper = np.round(gbest[2] + 1.96 * np.sqrt(var[2, 2]), 3)
        mu_lower = np.round(gbest[0] - 1.96 * np.sqrt(var[3, 3]), 3)
        mu_upper = np.round(gbest[0] + 1.96 * np.sqrt(var[3, 3]), 3)
        print("\nThe 95% CIs for activation strength k1 and k2:\n" +
            " k1 : (" + str(k1_lower) + ", " + str(k1_upper) + ")\n",
            "k2 : (" + str(k2_lower) + ", " + str(k2_upper) + ")\n"
             )
        result['k1_lower'] = k1_lower; result['k1_upper'] = k1_upper; result['k1_std'] = np.sqrt(var[1, 1])
        result['k2_lower'] = k2_lower; result['k2_upper'] = k2_upper; result['k2_std'] = np.sqrt(var[2, 2])
        result['mu_lower'] = mu_lower; result['mu_upper'] = mu_upper; result['mu_std'] = np.sqrt(var[3, 3])
        result['Fisher'] = 'Non-singular'
    else:
        var = fisher
        var[0, 0] = 1 / (var[0, 0] + 1e-100)
        var[1, 1] = 1 / (var[1, 1] + 1e-100)
        var[2, 2] = 1 / (var[2, 2] + 1e-100)
        var[3, 3] = 1 / (var[3, 3] + 1e-100)
        result['t0_std'] = np.sqrt(var[0, 0])
        k1_lower = np.round(gbest[1] - 1.96 * np.sqrt(var[1, 1]), 3)
        k1_upper = np.round(gbest[1] + 1.96 * np.sqrt(var[1, 1]), 3)
        k2_lower = np.round(gbest[2] - 1.96 * np.sqrt(var[2, 2]), 3)
        k2_upper = np.round(gbest[2] + 1.96 * np.sqrt(var[2, 2]), 3)
        mu_lower = np.round(gbest[0] - 1.96 * np.sqrt(var[3, 3]), 3)
        mu_upper = np.round(gbest[0] + 1.96 * np.sqrt(var[3, 3]), 3)
        print("\nThe 95% CIs for activation strength k1 and k2:\n" +
            " k1 : (" + str(k1_lower) + ", " + str(k1_upper) + ")\n",
            "k2 : (" + str(k2_lower) + ", " + str(k2_upper) + ")\n"
             )
        result['k1_lower'] = k1_lower; result['k1_upper'] = k1_upper; result['k1_std'] = np.sqrt(var[1, 1])
        result['k2_lower'] = k2_lower; result['k2_upper'] = k2_upper; result['k2_std'] = np.sqrt(var[2, 2])
        result['mu_lower'] = mu_lower; result['mu_upper'] = mu_upper; result['mu_std'] = np.sqrt(var[3, 3])
        result['Fisher'] = 'Singular'

    result['Transform'] = int(flag)
        ## SAVE ESTIMATION RESULTS
    ### Calculate new negative log-likelihood value
    mu_fit, k1_fit, k2_fit, t0_fit = gbest[:4]
    log_mut_fit = link((t), mu_fit, k1_fit, k2_fit, t0_fit)
    log_mut_fit = - log_mut_fit + np.log(np.max(y1) + 1)
    if marginal == "ZINB":
        #mut = np.maximum(np.exp(log_mut_fit) , 0.1)
        #phi = np.maximum((gbest[4]), 1)
        #p0 = phi / (mut + phi)
        #cache = nbinom.pmf(y1, phi, p0) + 1e-300

        ## Zero-inflation
        #p = 1 / (1 + np.exp(gbest[5] * np.log(mut) + gbest[6]))
        #result['negative_log_likelihood'] = - np.log(cache * (1 - p) + p * (y1 == 0)).sum()
        result['AIC'] = 2*result['negative_log_likelihood'] + 2*7
        
    elif marginal == "NB":
        #mut = np.maximum(np.exp(log_mut_fit) , 0.1)
        #phi = np.maximum((gbest[4]), 1)
        #p0 = mut / (mut + phi)
        #cache = nbinom.pmf(y1, phi, 1 - p0) + 1e-300
        #result['negative_log_likelihood'] = -np.log(cache).sum()
        result['AIC'] = 2*result['negative_log_likelihood'] + 2*6
    elif marginal == "ZIP":
        #mut = np.maximum(np.exp(log_mut_fit), 0.1)
        #cache = poisson.pmf(y1, mut) + 1e-300

        ## Zero-inflation
        #p = 1 / (1 + np.exp(gbest[4] * np.log(mut) + gbest[5]))

        #result['negative_log_likelihood'] =  - np.log(cache * (1 - p) + p * (y1 == 0)).sum()
        result['AIC'] = 2*result['negative_log_likelihood'] + 2*6
    else:
        #mut = np.maximum(np.exp(log_mut_fit) , 0.1)
        #result['negative_log_likelihood'] = -np.log(poisson.pmf(y1, mut) + 1e-300).sum()
        result['AIC'] = 2*result['negative_log_likelihood'] + 2*5

    with open(save_dir + str(gene_index - 1) + marginal + '.json', 'w') as fp:
        json.dump(result, fp)
        #w = csv.DictWriter(fp, result.keys())
        #w.writeheader()
        #w.writerow(result)

    return {"result": result, "fitted_values": log_mut_fit}

def parallel(args):
    print("Loading data......")
    data = pd.read_csv(args['data.dir'])
    print("Loading finished!")

    fitted_values = np.zeros((len(data.iloc[:, 1]), args['gene.end'] - args['gene.start']))
    fitted_values = pd.DataFrame(fitted_values)
    count = 0

    for i in range(args['gene.start']+1, args['gene.end']+1):
        output = main(gene_index=i,
             t=data.iloc[:, 1],
             y1 = np.floor(data.iloc[:, i]),
             gene_name = data.columns[i],
             marginal=args['model.marginal'],
             iter_num=args['model.iter'],
             save_dir=args['model.save_dir'],
             plot_args={
                'color': ['dodgerblue', 'skyblue', 'blue', 'violet'],
                'cmap': 'autumn',
             })
        fitted_values.iloc[:, count] = output['fitted_values']
        count += 1
    
    fitted_values.columns = data.columns[args['gene.start']+1: args['gene.end']+1]
    fitted_values.to_csv(args['model.save_dir'] + "fitted_mat.csv", index=False)

    return

