"""
Grouped boxplots
================

_thumb: .66, .45

"""
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms

import pandas as pd
import seaborn as sns


#xtickrotation = 0
#font_size = 12
#font_weight = 'bold'
#label_font_weight = 'bold'

#fig_size = (6, 4)


# styles
##plt.rcParams.update({'font.size': font_size})
##plt.rcParams.update({'font.weight': font_weight})
##plt.rcParams['axes.labelweight'] = label_font_weight
##
##plt.figure(num=None, figsize=(6, 3.8), dpi=300, facecolor='w', edgecolor='k')
# sns.set(style="whitegrid")

mystyle = {'axes.axisbelow': True,
           'axes.edgecolor': '0.0',
           'axes.facecolor': 'white',
           'axes.grid': True,
           'axes.labelcolor': '.0',
           'axes.spines.bottom': True,
           'axes.spines.left': True,
           'axes.spines.right': True,
           'axes.spines.top': True,
           'figure.facecolor': 'white',
           'font.family': ['sans-serif'],
           'font.sans-serif': ['Arial',
                               'DejaVu Sans',
                               'Liberation Sans',
                               'Bitstream Vera Sans',
                               'sans-serif'],
           'grid.color': '.7',
           'grid.linestyle': '--',
           'image.cmap': 'rocket',
           'lines.solid_capstyle': 'round',
           'patch.edgecolor': 'w',
           'patch.force_edgecolor': True,
           'text.color': '.00',
           'xtick.bottom': True,
           'xtick.color': '.15',
           'xtick.direction': 'out',
           'xtick.top': False,
           'ytick.color': '.15',
           'ytick.direction': 'out',
           'ytick.left': True,
           'ytick.right': False}


sns.set_style(mystyle)
# Load the example tips dataset
# tips = sns.load_dataset("https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv")
tips = pd.read_csv("RESULTS_modified.csv")

# Draw a nested boxplot to show bills by day and time
fig, ax = plt.subplots()
#sns.boxplot(x="Number of Requests", y="Link Utilization (%)", hue="Algorithm", data=tips, ax=ax)
#sns.pointplot(x="Number of Requests", y="Link Utilization (%)", hue="Algorithm", data=tips, linestyles='--', scale=0.4, ax=ax)
sns.barplot(x="Number of VNRs", y="Revenue To Cost Ratio (%)", hue="Algorithm",
            data=tips, ax=ax, palette=['C3', 'C0', 'C5', 'C1', 'C4', 'C2'])
ax.xaxis.label.set_size(18)
ax.yaxis.label.set_size(18)
ax.xaxis.set_tick_params(labelsize=18)
ax.yaxis.set_tick_params(labelsize=18)
#plt.legend(title="", fontsize=9.5, title_fontsize=9.5, loc='upper right', bbox_to_anchor=(0.99, 0.99))
# CODE FOR POINT PLOT
plt.legend(bbox_to_anchor=(0, 1, 1, 0), loc="lower left",
           mode="expand", ncol=3, fontsize=14)


# sns.despine(offset=10, trim=True)
# plt.show()
fig.set_size_inches(10, 6.5)
plt.savefig('graph_revenue_cost.eps', format='eps', dpi=300)
#plt.savefig('AVG_Migration_time_vs_Number_APPs_data_boxplot.eps', format='eps', dpi=300)
#plt.savefig('AVG_Migration_time_vs_Number_APPs_data_pointplot.eps', format='eps', dpi=300)
