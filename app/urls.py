from django.urls import path
from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('lancamentos/', views.LancamentosView.as_view(), name='lancamentos'),
    path('orcamento/', views.OrcamentoView.as_view(), name='orcamento'),
    path('orcamento/save/', views.OrcamentoView.as_view(), name='save_budget'),
    path('orcamento/add-category/', views.AddCategoryView.as_view(), name='add_category'),
    path('orcamento/edit-category/', views.EditCategoryView.as_view(), name='edit_category'),
    path('orcamento/delete-category/', views.DeleteCategoryView.as_view(), name='delete_category'),
    path('relatorios/', views.RelatoriosView.as_view(), name='relatorios'),
    path('metas/', views.MetasView.as_view(), name='metas'),
    path('save-goal/', views.SaveGoalView.as_view(), name='save_goal'),
    path('update-goal/<int:pk>/', views.UpdateGoalView.as_view(), name='update_goal'),
    path('delete-goal/<int:pk>/', views.DeleteGoalView.as_view(), name='delete_goal'),
    path('deposit-goal/', views.DepositGoalView.as_view(), name='deposit_goal'),
    path('update-deposit/<int:pk>/', views.UpdateDepositView.as_view(), name='update_deposit'),
    path('delete-deposit/<int:pk>/', views.DeleteDepositView.as_view(), name='delete_deposit'),
    path('alertas/', views.AlertasView.as_view(), name='alertas'),
    path('mark-alerts-read/', views.MarkAlertsReadView.as_view(), name='mark_alerts_read'),
    path('add-transaction/', views.AddTransactionView.as_view(), name='add_transaction'),
]
