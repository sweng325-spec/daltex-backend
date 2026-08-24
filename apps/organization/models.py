from django.db import models

class Branch(models.Model):
    
    branch_id = models.BigAutoField(primary_key=True)
    name_en = models.CharField(max_length=255, db_index=True)  # e.g., Headquarter, ElMohandseen
    name_ar = models.CharField(max_length=255, blank=True, null=True)  # 🌟 تم تعديله لـ name_an ليتطابق مع الـ Serializer
    location = models.CharField(max_length=255, blank=True, null=True)
    branch_code = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'branches'
        verbose_name_plural = "Branches"

    def __str__(self):
        return f"{self.name_en} ({self.branch_code})"


class Sector(models.Model):
    
    sector_id = models.BigAutoField(primary_key=True)
    sector_name = models.CharField(max_length=255, db_index=True,db_column='name') 
    # name_en = models.CharField(max_length=255, null=True, blank=True, default=None)     
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sectors'

    def __str__(self):
        return f"{self.sector_name} "


class Department(models.Model):
    
    id = models.BigAutoField(primary_key=True,db_column="dept_id")
    name = models.CharField(max_length=255, db_index=True) 
    # name_en = models.CharField(max_length=255, null=True, blank=True, default=None)    
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'departments'

    def __str__(self):
        return f"{self.name} ({self.sector.sector_name})"



class BranchStructure(models.Model):
    
    id = models.BigAutoField(db_column='structure_id', primary_key=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="structures")
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="structures",blank=True,null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="structures",blank=True,null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'branch_structure'
        
        unique_together = ('branch', 'sector', 'department')
        verbose_name = "Branch Structure"
        verbose_name_plural = "Branch Structures"

    def __str__(self):
        return f"{self.branch.name_en} -> {self.sector.sector_name} -> {self.name}"
    
    
class SubDepartment(models.Model):
    # If linking directly to your BranchStructure model:
    branch_structure = models.ForeignKey(
        'BranchStructure', 
        on_delete=models.CASCADE, 
        related_name='sub_departments'
    )
    name = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sub_departments'
        verbose_name = 'Sub Department'
        verbose_name_plural = 'Sub Departments'
        # Ensures duplicate sub-department names aren't created under the same structure
        unique_together = ('branch_structure', 'name')

    def __str__(self):
        return self.name